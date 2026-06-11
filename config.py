"""
config.py — Central configuration and environment variable management.
Load a .env file (if present) and expose typed settings across the app.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env from the project root (silently ignored if absent)
# ---------------------------------------------------------------------------
_ENV_PATH = Path(__file__).parent / ".env"
load_dotenv(_ENV_PATH)

# ---------------------------------------------------------------------------
# Telegram MTProto credentials
# Obtain from https://my.telegram.org → App configuration
# ---------------------------------------------------------------------------
TELEGRAM_API_ID: int = int(os.getenv("TELEGRAM_API_ID", "0"))
TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH", "")
TELEGRAM_SESSION_NAME: str = os.getenv("TELEGRAM_SESSION_NAME", "Vantavail_session")

# Owner username for presence detection
OWNER_USERNAME: str = os.getenv("OWNER_USERNAME", "")

# ---------------------------------------------------------------------------
# AI provider settings
# ---------------------------------------------------------------------------
AI_PROVIDER: str = os.getenv("AI_PROVIDER", "deepseek")

# Google Gemini configuration (optional)
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_BASE_URL: str = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/")

# DeepSeek/OpenRouter configuration (primary)
DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_MODEL: str = os.getenv("DEEPSEEK_MODEL", "openrouter/free")
DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://openrouter.ai/api/v1")

# ---------------------------------------------------------------------------
# Vantavail System Prompt
# ---------------------------------------------------------------------------
AI_SYSTEM_PROMPT: str = os.getenv(
    "AI_SYSTEM_PROMPT",
    (
        "You are Vantavail, Firaol's chat automation assistant. "
        "Always introduce yourself as 'Vantavail' when appropriate. "
        "After understanding what the user needs, always ask: "
        "'Would you like to proceed with this, or would you prefer to schedule an appointment?' "
        "Keep responses professional, friendly, and action-oriented. "
        "Never break character - you are Vantavail."
    ),
)

# ---------------------------------------------------------------------------
# SECURITY SETTINGS (Required for UI)
# ---------------------------------------------------------------------------

# Master security toggle
SECURITY_ENABLED: bool = os.getenv("SECURITY_ENABLED", "True").lower() == "true"

# Rate limiting
MAX_MESSAGES_PER_MINUTE: int = int(os.getenv("MAX_MESSAGES_PER_MINUTE", "10"))
RATE_LIMIT_WINDOW_SECONDS: int = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

# Auto-blocking
AUTO_BLOCK_THRESHOLD: int = int(os.getenv("AUTO_BLOCK_THRESHOLD", "5"))
BLOCK_DURATION_MINUTES: int = int(os.getenv("BLOCK_DURATION_MINUTES", "60"))

# Content scanning
SCAN_SUSPICIOUS_CONTENT: bool = os.getenv("SCAN_SUSPICIOUS_CONTENT", "True").lower() == "true"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DB_PATH: str = os.getenv("DB_PATH", str(Path(__file__).parent / "data" / "vantavail.db"))

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "ERROR")

# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
def validate_config() -> tuple[bool, list[str]]:
    errors = []
    
    if TELEGRAM_API_ID == 0:
        errors.append("TELEGRAM_API_ID is not set in .env")
    
    if not TELEGRAM_API_HASH:
        errors.append("TELEGRAM_API_HASH is not set in .env")
    
    if AI_PROVIDER == "deepseek" and not DEEPSEEK_API_KEY:
        errors.append("DEEPSEEK_API_KEY is not set in .env")
    
    if AI_PROVIDER == "gemini" and not GEMINI_API_KEY:
        errors.append("GEMINI_API_KEY is not set in .env")
    
    return len(errors) == 0, errors

def get_security_status() -> dict:
    """Return current security configuration status."""
    return {
        "security_enabled": SECURITY_ENABLED,
        "rate_limit": f"{MAX_MESSAGES_PER_MINUTE} per minute",
        "auto_block_threshold": AUTO_BLOCK_THRESHOLD,
        "block_duration_minutes": BLOCK_DURATION_MINUTES,
        "content_scanning": SCAN_SUSPICIOUS_CONTENT,
    }


def load_from_db(db):
    """Load settings from DB and override configuration variables dynamically."""
    global TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_NAME, OWNER_USERNAME
    global AI_PROVIDER, GEMINI_API_KEY, GEMINI_MODEL, GEMINI_BASE_URL
    global DEEPSEEK_API_KEY, DEEPSEEK_MODEL, DEEPSEEK_BASE_URL, AI_SYSTEM_PROMPT
    global SECURITY_ENABLED, MAX_MESSAGES_PER_MINUTE, RATE_LIMIT_WINDOW_SECONDS
    global AUTO_BLOCK_THRESHOLD, BLOCK_DURATION_MINUTES, SCAN_SUSPICIOUS_CONTENT

    val = db.get_setting("TELEGRAM_API_ID")
    if val is not None:
        try:
            TELEGRAM_API_ID = int(val)
        except ValueError:
            pass

    val = db.get_setting("TELEGRAM_API_HASH")
    if val is not None:
        TELEGRAM_API_HASH = val

    val = db.get_setting("TELEGRAM_SESSION_NAME")
    if val is not None:
        TELEGRAM_SESSION_NAME = val

    val = db.get_setting("OWNER_USERNAME")
    if val is not None:
        OWNER_USERNAME = val

    val = db.get_setting("AI_PROVIDER")
    if val is not None:
        AI_PROVIDER = val

    val = db.get_setting("GEMINI_API_KEY")
    if val is not None:
        GEMINI_API_KEY = val

    val = db.get_setting("GEMINI_MODEL")
    if val is not None:
        GEMINI_MODEL = val

    val = db.get_setting("GEMINI_BASE_URL")
    if val is not None:
        GEMINI_BASE_URL = val

    val = db.get_setting("DEEPSEEK_API_KEY")
    if val is not None:
        DEEPSEEK_API_KEY = val

    val = db.get_setting("DEEPSEEK_MODEL")
    if val is not None:
        DEEPSEEK_MODEL = val

    val = db.get_setting("DEEPSEEK_BASE_URL")
    if val is not None:
        DEEPSEEK_BASE_URL = val

    val = db.get_setting("ai_system_prompt")  # DB key is lowercase "ai_system_prompt"
    if val is not None:
        AI_SYSTEM_PROMPT = val

    val = db.get_setting("security_enabled")
    if val is not None:
        SECURITY_ENABLED = val.lower() == "true" or val == "1"

    val = db.get_setting("max_messages_per_minute")
    if val is not None:
        try:
            MAX_MESSAGES_PER_MINUTE = int(val)
        except ValueError:
            pass

    val = db.get_setting("auto_block_threshold")
    if val is not None:
        try:
            AUTO_BLOCK_THRESHOLD = int(val)
        except ValueError:
            pass

    val = db.get_setting("block_duration_minutes")
    if val is not None:
        try:
            BLOCK_DURATION_MINUTES = int(val)
        except ValueError:
            pass
            
    val = db.get_setting("scan_suspicious_content")
    if val is not None:
        SCAN_SUSPICIOUS_CONTENT = val.lower() == "true" or val == "1"