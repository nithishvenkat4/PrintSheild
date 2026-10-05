import time
from typing import Dict, List, Optional
from collections import defaultdict
from fastapi import Request
from app.core.exceptions import AppException, ErrorCode


class InMemoryRateLimiter:
    """
    In-memory rate limiter using sliding window timestamps.
    Keys can be IP addresses or user IDs.
    """
    def __init__(self):
        self._records: Dict[str, List[float]] = defaultdict(list)

    def check(self, key: str, max_requests: int, window_seconds: int = 60) -> None:
        now = time.time()
        window_start = now - window_seconds

        # Clean old timestamps
        timestamps = [ts for ts in self._records[key] if ts > window_start]
        self._records[key] = timestamps

        if len(timestamps) >= max_requests:
            raise AppException(
                status_code=429,
                code=ErrorCode.RATE_LIMITED,
                message=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds}s."
            )

        self._records[key].append(now)

    def clear(self):
        self._records.clear()


limiter = InMemoryRateLimiter()


def rate_limit(max_requests: int, window_seconds: int = 60, by_user: bool = False):
    """
    FastAPI dependency for rate limiting.
    """
    def dependency(request: Request):
        client_ip = request.client.host if request.client else "unknown"
        if by_user and hasattr(request.state, "user_id"):
            key = f"user:{request.state.user_id}:{request.url.path}"
        else:
            key = f"ip:{client_ip}:{request.url.path}"

        limiter.check(key, max_requests, window_seconds)

    return dependency
