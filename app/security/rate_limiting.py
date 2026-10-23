"""
Rate Limiting Security Module
Provides in-memory rate limiting to protect authentication endpoints from brute-force attacks.
"""

from collections import defaultdict
import time
from functools import wraps
from flask import request, jsonify

# Maps client IP -> list of request timestamps
_attempt_history = defaultdict(list)

def rate_limit(max_attempts=10, window_seconds=60):
    """Limit the number of attempts from a client IP within a sliding time window."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            ip = request.remote_addr or "127.0.0.1"
            now = time.time()
            window_start = now - window_seconds
            
            # Filter attempts older than the window
            attempts = [t for t in _attempt_history[ip] if t > window_start]
            _attempt_history[ip] = attempts

            if len(attempts) >= max_attempts:
                retry_after = int(attempts[0] + window_seconds - now) + 1
                return jsonify({
                    "error": "Too many requests. Please wait before trying again.",
                    "retry_after_seconds": max(1, retry_after)
                }), 429

            _attempt_history[ip].append(now)
            return f(*args, **kwargs)
        return wrapped
    return decorator

def clear_rate_limits():
    """Reset rate limiting state (useful for test suites)."""
    _attempt_history.clear()
