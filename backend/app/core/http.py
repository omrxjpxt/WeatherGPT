import httpx
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class HttpClientManager:
    """
    Application-lifetime HTTP connection pool manager.
    Maintains a shared httpx.AsyncClient with keep-alive limits across providers.
    Ensures safe initialization on startup and graceful closing on shutdown.
    """
    _client: Optional[httpx.AsyncClient] = None

    @classmethod
    async def initialize(cls, timeout: float = 10.0, max_keepalive: int = 20, max_connections: int = 50) -> httpx.AsyncClient:
        if cls._client is None or cls._client.is_closed:
            limits = httpx.Limits(max_keepalive_connections=max_keepalive, max_connections=max_connections)
            cls._client = httpx.AsyncClient(timeout=timeout, limits=limits)
            logger.info("Shared HttpClientManager initialized with connection pooling.")
        return cls._client

    @classmethod
    async def close(cls) -> None:
        if cls._client is not None and not cls._client.is_closed:
            await cls._client.aclose()
            logger.info("Shared HttpClientManager closed gracefully.")
        cls._client = None

    @classmethod
    def get_client(cls) -> Optional[httpx.AsyncClient]:
        if cls._client is not None and not cls._client.is_closed:
            return cls._client
        return None
