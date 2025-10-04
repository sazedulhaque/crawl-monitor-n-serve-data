"""
Rate limiter configuration module.

This module is separate from main.py to avoid circular imports.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Create global rate limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/hour"],  # Global default: 100 requests per hour
    storage_uri="memory://",
)
