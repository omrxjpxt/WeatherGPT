import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from fastapi import Request, HTTPException, status
from app.core.config import settings


class InMemoryRateLimiter:
    """
    Lightweight in-memory sliding window rate limiter.
    Distinguishes authenticated requests from anonymous requests.
    Provides test resets and configurable bypasses.
    """

    def __init__(self):
        # Maps client_key -> list of timestamps (float epoch seconds)
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def reset(self):
        """Clears all tracked requests. Useful for deterministic testing."""
        self._requests.clear()

    def get_client_key(self, request: Request) -> Tuple[str, bool]:
        """
        Returns (client_identifier, is_authenticated).
        Uses Bearer token prefix for authenticated users, IP address for anonymous.
        """
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            if token:
                # Use a truncated token hash/key to avoid logging full credentials
                return f"auth:{token[:24]}", True

        client_host = request.client.host if request.client else "127.0.0.1"
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            client_host = forwarded_for.split(",")[0].strip()
        return f"ip:{client_host}", False

    def is_rate_limited(
        self, request: Request, custom_limit: Optional[int] = None
    ) -> Tuple[bool, int]:
        """
        Checks if the request exceeds the allowed rate limit.
        Returns (is_limited, retry_after_seconds).
        """
        if not settings.rate_limit_enabled:
            return False, 0

        client_key, is_auth = self.get_client_key(request)
        now = time.time()
        window_seconds = 60.0

        if custom_limit is not None:
            limit = custom_limit
        else:
            limit = (
                settings.rate_limit_per_minute_authenticated
                if is_auth
                else settings.rate_limit_per_minute_anonymous
            )

        # Filter out timestamps older than window
        timestamps = [t for t in self._requests[client_key] if now - t < window_seconds]

        if len(timestamps) >= limit:
            oldest = timestamps[0]
            retry_after = max(1, int(window_seconds - (now - oldest)))
            self._requests[client_key] = timestamps
            return True, retry_after

        timestamps.append(now)
        self._requests[client_key] = timestamps
        return False, 0


rate_limiter = InMemoryRateLimiter()


async def check_rate_limit(request: Request):
    """
    FastAPI dependency for expensive endpoints.
    """
    is_limited, retry_after = rate_limiter.is_rate_limited(request)
    if is_limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )
