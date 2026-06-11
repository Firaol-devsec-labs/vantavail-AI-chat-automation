"""
core/ai_handler.py
Unified async wrapper for Gemini and DeepSeek AI APIs.
"""

import asyncio
import logging
from typing import Optional, Tuple

import aiohttp
import config

logger = logging.getLogger(__name__)
logger.disabled = True

_RETRY_ATTEMPTS = 2
_RETRY_DELAY = 1


class AIHandler:
    """Routes AI completion requests to the configured provider."""

    def __init__(self, provider: Optional[str] = None):
        self.provider = provider
        self.pending_appointments = {}
        self.user_languages = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def get_reply(self, conversation_history: list[dict], system_prompt: Optional[str] = None, 
                        user_id: Optional[int] = None, security_manager: Optional[object] = None) -> str:
        """Generate an AI reply given conversation history."""
        prompt = system_prompt or config.AI_SYSTEM_PROMPT
        provider = (self.provider or config.AI_PROVIDER).lower()

        for attempt in range(1, _RETRY_ATTEMPTS + 1):
            try:
                if provider == "gemini":
                    return await self._call_gemini(conversation_history, prompt)
                elif provider == "deepseek":
                    return await self._call_deepseek(conversation_history, prompt)
                else:
                    return f"Unknown AI provider: {provider}"
                    
            except asyncio.TimeoutError:
                if attempt == _RETRY_ATTEMPTS:
                    return "⏰ The AI service is taking too long. Please try again."
                await asyncio.sleep(0.5)
                
            except aiohttp.ClientResponseError as e:
                if e.status == 429:
                    if attempt == _RETRY_ATTEMPTS:
                        return "📊 The AI service is busy. Please try again in a few seconds."
                    await asyncio.sleep(1)
                else:
                    if attempt == _RETRY_ATTEMPTS:
                        return f"🔌 AI service error: {e.status}. Please try again."
                    await asyncio.sleep(0.5)
                    
            except Exception as e:
                if attempt == _RETRY_ATTEMPTS:
                    return "I'm here to help! Could you please rephrase that?"
                await asyncio.sleep(0.5)
        
        return "I'm ready to help! What would you like to do today?"

    # ------------------------------------------------------------------
    # Google Gemini (Fixed - Working)
    # ------------------------------------------------------------------

    async def _call_gemini(self, history: list[dict], system_prompt: str) -> str:
        """Call Google Gemini API directly."""
        if not config.GEMINI_API_KEY:
            return "Gemini API key not configured. Get one from https://aistudio.google.com/"
        
        # Build URL
        base_url = config.GEMINI_BASE_URL.rstrip("/")
        url = f"{base_url}models/{config.GEMINI_MODEL}:generateContent?key={config.GEMINI_API_KEY}"
        
        # Convert conversation history to Gemini format (strictly alternate user and model roles)
        contents = []
        for msg in history[-10:]:  # Last 10 messages for speed
            role = "user" if msg["role"] == "user" else "model"
            if contents and contents[-1]["role"] == role:
                contents[-1]["parts"][0]["text"] += "\n" + msg["content"]
            else:
                contents.append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })
        
        # Build payload
        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 256,
                "topP": 0.95,
                "topK": 40
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}
            ]
        }
        
        headers = {"Content-Type": "application/json"}
        timeout = aiohttp.ClientTimeout(total=15, connect=5)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=timeout) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    print(f"Gemini API Error {resp.status}: {error_text[:200]}")
                    raise aiohttp.ClientResponseError(status=resp.status, message=error_text)
                
                data = await resp.json()
                
                try:
                    # Extract response text
                    response_text = data["candidates"][0]["content"]["parts"][0]["text"]
                    if response_text and response_text.strip():
                        return response_text.strip()
                    return "I received an empty response. Please try again."
                except (KeyError, IndexError) as e:
                    print(f"Failed to parse Gemini response: {data}")
                    return "I received a malformed response. Please try again."

    # ------------------------------------------------------------------
    # DeepSeek (Backup - via OpenRouter)
    # ------------------------------------------------------------------

    async def _call_deepseek(self, history: list[dict], system_prompt: str) -> str:
        """Call DeepSeek via OpenRouter (fallback)."""
        base_url = config.DEEPSEEK_BASE_URL.rstrip("/")
        
        if base_url.endswith("/v1"):
            url = f"{base_url}/chat/completions"
        elif "/chat/completions" in base_url:
            url = base_url
        else:
            url = f"{base_url}/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {config.DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": config.DEEPSEEK_MODEL,
            "messages": [{"role": "system", "content": system_prompt}, *history[-10:]],
            "temperature": 0.7,
            "max_tokens": 256,
        }
        
        timeout = aiohttp.ClientTimeout(total=15, connect=5)
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=timeout) as resp:
                if resp.status != 200:
                    error_text = await resp.text()
                    raise aiohttp.ClientResponseError(status=resp.status, message=error_text)
                
                data = await resp.json()
                
                try:
                    content = data.get("choices", [{}])[0].get("message", {}).get("content")
                    if content and content.strip():
                        return content.strip()
                    return "I received an empty response. Please try again."
                except Exception:
                    return "I received a malformed response. Please try again."

    # ------------------------------------------------------------------
    # Appointment Handling
    # ------------------------------------------------------------------

    def detect_appointment_request(self, message: str) -> Tuple[bool, Optional[str]]:
        keywords = ['appointment', 'schedule', 'book', 'meeting', 'call', 'talk', 'discuss', 'consult']
        for keyword in keywords:
            if keyword in message.lower():
                return True, keyword
        return False, None

    def set_pending_appointment(self, user_id: int, context: str):
        self.pending_appointments[user_id] = context

    def get_pending_appointment(self, user_id: int) -> Optional[str]:
        return self.pending_appointments.get(user_id)

    def clear_pending_appointment(self, user_id: int):
        if user_id in self.pending_appointments:
            del self.pending_appointments[user_id]