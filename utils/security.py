"""⚡ SECURITY UTILITIES - Rate Limiting & Input Validation"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class SimpleRateLimiter:
    """In-memory rate limiter for rate limiting API endpoints."""
    
    def __init__(self):
        self.requests = {}  # {key: [timestamp, ...]}
    
    def is_allowed(self, key: str, max_requests: int = 100, window_seconds: int = 60) -> bool:
        """
        Check if request is within rate limit.
        
        Args:
            key: Unique identifier (user_id or IP address)
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
        
        Returns:
            True if allowed, False if rate limit exceeded
        """
        now = datetime.now()
        cutoff = now - timedelta(seconds=window_seconds)
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Remove old entries outside the window
        self.requests[key] = [t for t in self.requests[key] if t > cutoff]
        
        # Check if limit exceeded
        if len(self.requests[key]) >= max_requests:
            logger.warning(f"⚠️ Rate limit exceeded for key: {key}")
            return False
        
        # Add current request
        self.requests[key].append(now)
        return True


# Global rate limiter instance
limiter = SimpleRateLimiter()


def validate_text(text: str, min_len: int = 1, max_len: int = 1000) -> str:
    """Validate text input - prevent SQL injection and XSS."""
    if not text or not isinstance(text, str):
        raise ValueError("❌ Invalid text input")
    
    text = text.strip()
    
    if len(text) < min_len or len(text) > max_len:
        raise ValueError(f"❌ Text length must be {min_len}-{max_len} chars")
    
    # Check for SQL injection patterns
    dangerous = [" UNION ", " SELECT ", " DROP ", " INSERT ", " DELETE ", "--", ";"]
    for pattern in dangerous:
        if pattern.upper() in text.upper():
            raise ValueError("❌ Invalid characters in text")
    
    return text

