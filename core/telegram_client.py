"""
core/telegram_client.py
Secure Telegram client with security filtering - FAST RESPONSES.
"""

import asyncio
import logging
from typing import Optional, Callable, Dict, List

from telethon import TelegramClient, events
from telethon.tl.types import User

import config
from core.ai_handler import AIHandler
from core.security import SecurityManager
from database.db_manager import DBManager

# COMPLETELY SILENT
logging.getLogger("telethon").disabled = True
logger = logging.getLogger(__name__)
logger.disabled = True


class TelegramBotClient:
    """Secure Telegram bot client with security features and fast responses."""

    def __init__(
        self,
        db: DBManager,
        on_log: Optional[Callable[[dict], None]] = None,
        on_status_change: Optional[Callable[[str], None]] = None,
        on_security_event: Optional[Callable[[int, str, str, str, int], None]] = None,
    ):
        self._db = db
        self._on_log = on_log
        self._on_status = on_status_change
        self._on_security = on_security_event
        self._ai = AIHandler()
        self._security = SecurityManager(db)
        self._client: Optional[TelegramClient] = None
        self._active = False
        self._scope_mode: str = db.get_setting("scope_mode", "exclude")
        self._ignore_groups: bool = db.get_setting("ignore_groups", "1") == "1"
        self._respond_to_new: bool = db.get_setting("respond_to_new_users", "1") == "1"
        self._respond_to_existing: bool = db.get_setting("respond_to_existing", "1") == "1"
        self._existing_user_ids = set()
        self._conversation_contexts: Dict[int, List[dict]] = {}
        self._max_context = 10
        self._processing = set()

    async def connect(self):
        if not config.TELEGRAM_API_ID or not config.TELEGRAM_API_HASH:
            raise ValueError("TELEGRAM_API_ID and TELEGRAM_API_HASH must be set")

        self._client = TelegramClient(
            config.TELEGRAM_SESSION_NAME,
            config.TELEGRAM_API_ID,
            config.TELEGRAM_API_HASH,
        )
        await self._client.start()
        me = await self._client.get_me()
        if self._on_status:
            self._on_status(f"CONNECTED — @{me.username}")
        
        # Cache existing dialog user IDs (limit to 200 for speed)
        self._existing_user_ids.clear()
        try:
            async for dialog in self._client.iter_dialogs(limit=200):
                if dialog.is_user:
                    self._existing_user_ids.add(dialog.id)
        except Exception as e:
            print(f"Error fetching dialogs: {e}")
            
        self._register_handlers()

    async def disconnect(self):
        if self._client and self._client.is_connected():
            await self._client.disconnect()
        if self._on_status:
            self._on_status("DISCONNECTED")

    def set_active(self, active: bool):
        self._active = active
        self._db.set_setting("automation_active", "1" if active else "0")

    @property
    def is_active(self) -> bool:
        return self._active

    def set_ignore_groups(self, ignore: bool):
        self._ignore_groups = ignore
        self._db.set_setting("ignore_groups", "1" if ignore else "0")

    def reload_filters(self):
        self._ignore_groups = self._db.get_setting("ignore_groups", "1") == "1"
        self._respond_to_new = self._db.get_setting("respond_to_new_users", "1") == "1"
        self._respond_to_existing = self._db.get_setting("respond_to_existing", "1") == "1"

    def set_scope_mode(self, mode: str):
        self._scope_mode = mode
        self._db.set_setting("scope_mode", mode)

    def _is_allowed(self, chat_id: int) -> bool:
        excluded = self._db.is_excluded(chat_id)
        if self._scope_mode == "exclude":
            return not excluded
        return excluded

    async def _safe_reply(self, event, message: str) -> bool:
        try:
            await event.reply(message)
            return True
        except Exception:
            try:
                await event.client.send_message(event.chat_id, message)
                return True
            except Exception:
                return False

    async def _safe_typing(self, event):
        try:
            async with event.client.action(event.chat_id, "typing"):
                await asyncio.sleep(0.1)
        except Exception:
            pass

    def _send_security_notification(self, user_id: int, username: str, action: str, reason: str, duration: int = None):
        if self._on_security:
            self._on_security(user_id, username, action, reason, duration)

    async def _handle_command(self, event, command: str, user_id: int, username: str) -> bool:
        if command == "/status":
            is_blocked, block_reason = self._security.is_blocked(user_id)
            status_text = (
                f"🤖 **Vantavail Status**\n\n"
                f"• Automation: {'🟢 ACTIVE' if self._active else '🔴 INACTIVE'}\n"
                f"• Model: {config.DEEPSEEK_MODEL}\n"
                f"• Security: {'🟢 ENABLED' if config.SECURITY_ENABLED else '🔴 DISABLED'}\n"
            )
            if is_blocked:
                status_text += f"\n⚠️ You are blocked: {block_reason}"
            await self._safe_reply(event, status_text)
            return True
            
        elif command == "/reset":
            if user_id in self._conversation_contexts:
                self._conversation_contexts[user_id] = []
                await self._safe_reply(event, "✅ Conversation cleared!")
            else:
                await self._safe_reply(event, "No conversation to clear.")
            return True
            
        elif command == "/joke":
            response = await self._ai.get_reply(
                [{"role": "user", "content": "Tell me a funny joke"}],
                user_id=user_id,
                security_manager=self._security
            )
            await self._safe_reply(event, response)
            return True
            
        return False

    def _register_handlers(self):
        @self._client.on(events.NewMessage(incoming=True))
        async def handle_message(event):
            if not self._active:
                return

            # Get sender safely - FIXED: handle None sender
            try:
                sender = await event.get_sender()
            except Exception:
                sender = None
            
            chat_id = event.chat_id
            user_id = sender.id if sender and hasattr(sender, 'id') else chat_id
            
            # Ignore messages from bots completely (prevent loops and spam from other bots)
            if sender and getattr(sender, 'bot', False):
                return
            
            # Get username safely - FIXED: handle None sender and missing attributes
            if sender:
                username = getattr(sender, 'username', None) or getattr(sender, 'first_name', None) or str(user_id)
            else:
                username = str(user_id)
            
            text = (event.raw_text or "").strip()
            is_group = event.is_group or event.is_channel
            
            if not text:
                return
            
            # Prevent duplicate processing
            if user_id in self._processing:
                return
            self._processing.add(user_id)
            
            try:
                # Check if blocked
                is_blocked, block_reason = self._security.is_blocked(user_id)
                if is_blocked:
                    await self._safe_reply(event, f"⚠️ You are blocked. Reason: {block_reason}")
                    return
 
                # Check rate limit
                if config.SECURITY_ENABLED:
                    is_limited, count = self._security.check_rate_limit(user_id)
                    if is_limited:
                        await self._safe_reply(event, "⚠️ You are sending messages too quickly. Please wait.")
                        self._db.log_security_event(user_id, username, "rate_limit_exceeded", f"Rate limit window hit. Message: {text[:50]}", "low")
                        self._send_security_notification(user_id, username, "rate_limit_exceeded", "Rate limit exceeded")
                        return
                    self._security.record_message(user_id)
 
                # Scan message content
                if config.SECURITY_ENABLED:
                    is_suspicious, pattern_type, severity = self._security.scan_message(text, user_id, username)
                    if is_suspicious:
                        self._send_security_notification(user_id, username, pattern_type, f"Violation: {text[:50]}")
                        if self._security.should_auto_block(user_id, username, severity):
                            await self._safe_reply(event, f"⚠️ You have been auto-blocked due to security violations: {pattern_type}")
                            return
                        else:
                            await self._safe_reply(event, f"⚠️ Warning: Suspicious content detected ({pattern_type}). Please keep conversation professional.")
                            return
                
                # Handle commands
                if text.startswith('/'):
                    await self._handle_command(event, text.lower(), user_id, username)
                    return
                
                # Group handling
                if is_group:
                    if self._ignore_groups:
                        return
                    try:
                        bot_me = await self._client.get_me()
                        is_mentioned = False
                        if bot_me and bot_me.username:
                            is_mentioned = f"@{bot_me.username}" in text
                        if not is_mentioned:
                            return
                    except Exception:
                        return
                
                # Private chat scope
                if not is_group and not self._is_allowed(chat_id):
                    return

                # Filter by sender type: new user vs. existing dialog
                is_existing_user = user_id in self._existing_user_ids
                if is_existing_user:
                    if not self._respond_to_existing:
                        return
                else:
                    if not self._respond_to_new:
                        return
                    # Add to cached set so we keep responding to them in this session
                    self._existing_user_ids.add(user_id)

                # Check if user is in pending appointment flow (waiting for details)
                pending_state = self._ai.get_pending_appointment(user_id)
                if pending_state == "waiting_for_details":
                    await self._safe_typing(event)
                    
                    extraction_prompt = (
                        "You are an assistant extracting appointment details. "
                        "Given the user's message, extract the preferred date/time and the reason/description of the appointment. "
                        "Respond ONLY in JSON format: {\"date_time\": \"...\", \"description\": \"...\"}. "
                        "If you cannot determine the date/time, set it to 'Not specified'. "
                        "If you cannot determine the description, use the user's text. "
                        "Do not include any explanation or markdown formatting, just the raw JSON."
                    )
                    
                    try:
                        raw_json = await self._ai.get_reply(
                            [{"role": "user", "content": text}],
                            system_prompt=extraction_prompt
                        )
                        import json
                        clean_json = raw_json.strip()
                        if clean_json.startswith("```json"):
                            clean_json = clean_json[7:]
                        if clean_json.endswith("```"):
                            clean_json = clean_json[:-3]
                        clean_json = clean_json.strip()
                        
                        data = json.loads(clean_json)
                        date_time = data.get("date_time", "Not specified")
                        description = data.get("description", text)
                    except Exception:
                        date_time = "Not specified"
                        description = text
                    
                    self._db.add_appointment(user_id, username, date_time, description)
                    self._ai.clear_pending_appointment(user_id)
                    
                    reply = (
                        f"📅 **Appointment Request Received!**\n\n"
                        f"• **Date/Time:** {date_time}\n"
                        f"• **Description:** {description}\n\n"
                        f"Firaol has been notified. Thank you!"
                    )
                    await self._safe_reply(event, reply)
                    
                    log_entry = {
                        "chat_id": chat_id,
                        "sender": username,
                        "user_message": text,
                        "ai_response": reply,
                        "provider": config.AI_PROVIDER,
                    }
                    self._db.log_response(**log_entry)
                    if self._on_log:
                        self._on_log(log_entry)
                    return
                
                # Intercept keywords to schedule an appointment
                is_appt, keyword = self._ai.detect_appointment_request(text)
                if is_appt:
                    self._ai.set_pending_appointment(user_id, "waiting_for_details")
                    reply = (
                        "📅 **Schedule an Appointment**\n\n"
                        "I'd be happy to schedule an appointment for you with Firaol. "
                        "Please reply with your preferred **date & time** and a **brief description** of what you'd like to discuss."
                    )
                    await self._safe_reply(event, reply)
                    return
                
                # Send typing indicator quickly
                await self._safe_typing(event)
                
                # Maintain context
                if user_id not in self._conversation_contexts:
                    self._conversation_contexts[user_id] = []
                
                self._conversation_contexts[user_id].append({
                    "role": "user",
                    "content": text
                })
                
                if len(self._conversation_contexts[user_id]) > self._max_context:
                    self._conversation_contexts[user_id] = self._conversation_contexts[user_id][-self._max_context:]
                
                # Get AI response
                reply = await self._ai.get_reply(
                    self._conversation_contexts[user_id],
                    user_id=user_id,
                    security_manager=self._security
                )
                
                if reply:
                    self._conversation_contexts[user_id].append({
                        "role": "assistant",
                        "content": reply
                    })
                    
                    if len(self._conversation_contexts[user_id]) > self._max_context:
                        self._conversation_contexts[user_id] = self._conversation_contexts[user_id][-self._max_context:]
                    
                    success = await self._safe_reply(event, reply)
                    
                    if success:
                        log_entry = {
                            "chat_id": chat_id,
                            "sender": username,
                            "user_message": text,
                            "ai_response": reply,
                            "provider": config.AI_PROVIDER,
                        }
                        self._db.log_response(**log_entry)
                        if self._on_log:
                            self._on_log(log_entry)
                else:
                    await self._safe_reply(event, "I'm here! What would you like to do?")
                    
            except Exception as e:
                print(f"Error: {e}")
                await self._safe_reply(event, "I'm here to help! Could you please rephrase that?")
            finally:
                self._processing.discard(user_id)