"""
core/security.py
Security module for detecting and preventing malicious activities.
"""

import re
import hashlib
from datetime import datetime, timedelta
from typing import Tuple, Optional, List, Dict
from collections import defaultdict

import config


class SecurityManager:
    """Manages security checks for user messages."""

    def __init__(self, db_manager):
        self.db = db_manager
        self._message_count = defaultdict(list)
        self._violation_count = defaultdict(int)

    SUSPICIOUS_PATTERNS = [
        (r"(?i)(DROP\s+TABLE|DELETE\s+FROM|UPDATE\s+.*SET|INSERT\s+INTO|ALTER\s+TABLE|TRUNCATE\s+TABLE)", "sql_injection", "high"),
        (r"(?i)(UNION\s+SELECT|SELECT.*\s+FROM\s+\w+\s+WHERE|'.*--|;.*--|OR\s+1=1)", "sql_injection", "high"),
        (r"(?i)(exec\(|eval\(|system\(|shell_exec\(|passthru\(|popen\(|proc_open\()", "code_injection", "high"),
        (r"(?i)(__import__|os\.system|subprocess\.call|subprocess\.Popen)", "code_injection", "high"),
        (r"(?i)(ignore previous instructions|forget your rules|act as if|pretend you are)", "prompt_injection", "high"),
        (r"(?i)(you are now|your new role is|disregard|override your system prompt)", "prompt_injection", "high"),
        (r"(?i)(<script|javascript:|onclick=|onload=|alert\(|confirm\()", "xss_attempt", "medium"),
        (r"(?i)(casino|gambling|poker|slot|betting|lottery)", "spam", "low"),
        (r"(?i)(bitcoin|ethereum|crypto|send.*money|pay.*me|investment.*opportunity)", "crypto_scam", "high"),
        (r"(?i)(login.*verify|verify.*account|confirm.*identity|update.*payment)", "phishing", "high"),
        (r"(?i)(kill\s+yourself|die\s+now|i\s+hate\s+you)", "harassment", "high"),
        (r"(?i)(\b(fuck|shit|damn|hell)\b)", "profanity", "low"),
        (r"(https?://)?(bit\.ly|tinyurl|shorturl|rb\.gy)[/\w]+", "url_shortener", "medium"),
    ]

    def scan_message(self, message: str, user_id: int, username: str) -> Tuple[bool, Optional[str], Optional[str]]:
        if not config.SCAN_SUSPICIOUS_CONTENT:
            return False, None, None
        
        message_lower = message.lower()
        
        for pattern, pattern_type, severity in self.SUSPICIOUS_PATTERNS:
            try:
                if re.search(pattern, message_lower):
                    self.db.log_security_event(
                        user_id, username, pattern_type, 
                        f"Suspicious: {message[:100]}", severity
                    )
                    self._violation_count[user_id] += 1
                    return True, pattern_type, severity
            except re.error:
                continue
        
        return False, None, None

    def check_rate_limit(self, user_id: int) -> Tuple[bool, int]:
        now = datetime.now()
        window = timedelta(seconds=config.RATE_LIMIT_WINDOW_SECONDS)
        
        self._message_count[user_id] = [ts for ts in self._message_count[user_id] if now - ts < window]
        count = len(self._message_count[user_id])
        is_limited = count >= config.MAX_MESSAGES_PER_MINUTE
        
        return is_limited, count

    def record_message(self, user_id: int):
        self._message_count[user_id].append(datetime.now())
        now = datetime.now()
        window = timedelta(seconds=config.RATE_LIMIT_WINDOW_SECONDS)
        self._message_count[user_id] = [ts for ts in self._message_count[user_id] if now - ts < window]

    def is_blocked(self, user_id: int) -> Tuple[bool, Optional[str]]:
        return self.db.is_user_blocked(user_id)

    def should_auto_block(self, user_id: int, username: str, severity: str = "medium") -> bool:
        if severity == "high":
            violations = self.db.get_violation_count(user_id, "high", hours=24)
            if violations >= 2:
                self.db.block_user(user_id, username, f"Auto-blocked after {violations} high-severity violations", config.BLOCK_DURATION_MINUTES)
                return True
        elif severity == "medium":
            violations = self.db.get_violation_count(user_id, hours=24)
            if violations >= config.AUTO_BLOCK_THRESHOLD:
                self.db.block_user(user_id, username, f"Auto-blocked after {violations} violations", config.BLOCK_DURATION_MINUTES)
                return True
        return False

    def get_user_violation_count(self, user_id: int) -> int:
        return self.db.get_violation_count(user_id, hours=24)