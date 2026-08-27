from typing import Any, Optional, Dict
from datetime import datetime, timezone, timedelta
import asyncio
from app.cache.interface import CacheInterface

class MemoryCache(CacheInterface):
    def __init__(self):
        self._store: Dict[str, dict] = {}
        self._lock = asyncio.Lock()
        
    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            if key in self._store:
                item = self._store[key]
                if item["expires_at"] > datetime.now(timezone.utc):
                    return item["value"]
                else:
                    del self._store[key]
        return None
        
    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        async with self._lock:
            self._store[key] = {
                "value": value,
                "expires_at": datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
            }
            
    async def invalidate(self, key: str) -> None:
        async with self._lock:
            if key in self._store:
                del self._store[key]
