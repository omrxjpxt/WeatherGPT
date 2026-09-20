import pytest
import time
from unittest.mock import MagicMock
from fastapi import Request

from app.core.rate_limiter import InMemoryRateLimiter
from app.core.config import settings


def _make_mock_request(client_ip="127.0.0.1", forwarded_for=None, auth_token=None):
    req = MagicMock(spec=Request)
    req.client = MagicMock()
    req.client.host = client_ip
    headers = {}
    if forwarded_for:
        headers["X-Forwarded-For"] = forwarded_for
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    req.headers = headers
    return req


def test_rate_limiter_prunes_expired_keys():
    limiter = InMemoryRateLimiter(max_keys=100)
    now = time.time()

    # Seed 5 client keys with timestamps older than 60s
    limiter._requests["ip:old_client_1"] = [now - 120.0, now - 90.0]
    limiter._requests["ip:old_client_2"] = [now - 80.0]
    limiter._requests["ip:active_client"] = [now - 10.0]

    # Force prune
    limiter._prune_expired_keys(now=now, window_seconds=60.0)

    # Assert old entries removed, active entry kept
    assert "ip:old_client_1" not in limiter._requests
    assert "ip:old_client_2" not in limiter._requests
    assert "ip:active_client" in limiter._requests


def test_rate_limiter_bounds_maximum_keys():
    # Limiter with hard cap of 5 keys
    limiter = InMemoryRateLimiter(max_keys=5)
    now = time.time()

    for i in range(10):
        req = _make_mock_request(client_ip=f"192.168.1.{i}")
        limiter.is_rate_limited(req, custom_limit=10)

    # Size must not exceed max_keys
    assert len(limiter._requests) <= 5


def test_rate_limiter_ignores_forwarded_for_from_untrusted_proxy():
    limiter = InMemoryRateLimiter()

    # Request from an untrusted public IP pretending to be 1.1.1.1
    req = _make_mock_request(client_ip="203.0.113.50", forwarded_for="1.1.1.1")
    key, is_auth = limiter.get_client_key(req)

    # Must attribute to actual connecting client (203.0.113.50), NOT the spoofed header (1.1.1.1)
    assert key == "ip:203.0.113.50"
    assert is_auth is False


def test_rate_limiter_honors_forwarded_for_from_trusted_proxy():
    limiter = InMemoryRateLimiter()

    # Request from 127.0.0.1 (in settings.trusted_proxies) with forwarded-for header
    req = _make_mock_request(client_ip="127.0.0.1", forwarded_for="198.51.100.25")
    key, is_auth = limiter.get_client_key(req)

    # Should trust the forwarded IP
    assert key == "ip:198.51.100.25"
    assert is_auth is False
