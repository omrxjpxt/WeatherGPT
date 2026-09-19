import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from app.core.logging import redact_sensitive_value, redact_sensitive_processor


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_request_id_generated_when_absent():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        assert "X-Request-Id" in res.headers
        req_id = res.headers["X-Request-Id"]
        assert len(req_id) > 10


@pytest.mark.asyncio
async def test_request_id_preserved_when_supplied():
    custom_id = "custom-trace-id-12345"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.get("/api/v1/health", headers={"X-Request-Id": custom_id})
        assert res.status_code == 200
        assert res.headers.get("X-Request-Id") == custom_id


@pytest.mark.asyncio
async def test_cors_headers_handling():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Preflight OPTIONS request from configured origin
        res = await client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"

        # Preflight from disallowed origin
        res_disallowed = await client.options(
            "/api/v1/health",
            headers={
                "Origin": "https://malicious-hacker-site.com",
                "Access-Control-Request-Method": "GET",
            }
        )
        assert res_disallowed.headers.get("access-control-allow-origin") != "https://malicious-hacker-site.com"


def test_logging_redaction_processor():
    # 1. Direct sensitive key names
    assert redact_sensitive_value("authorization", "Bearer my-secret-token") == "[REDACTED]"
    assert redact_sensitive_value("api_key", "secret-key-123") == "[REDACTED]"
    assert redact_sensitive_value("gemini_api_key", "AIzaSyD-1234567890abcdefghijklmnopqr") == "[REDACTED]"
    assert redact_sensitive_value("password", "supersecret") == "[REDACTED]"

    # 2. String pattern redaction inside arbitrary text
    text_with_bearer = "User sent request with Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    redacted_text = redact_sensitive_value("message", text_with_bearer)
    assert "Bearer [REDACTED]" in redacted_text
    assert "eyJhbG" not in redacted_text

    text_with_google_key = "Connecting with Google Maps key AIzaSyDabcdefghijklmnopqrstuvwxyz1234567"
    redacted_key_text = redact_sensitive_value("log", text_with_google_key)
    assert "[REDACTED]" in redacted_key_text
    assert "AIzaSyD" not in redacted_key_text

    # 3. Full dictionary event dict through structlog processor
    event_dict = {
        "event": "Authentication check failed",
        "authorization": "Bearer token-value",
        "token": "raw-token-123",
        "headers": {
            "api_key": "my-secret",
            "safe_header": "application/json"
        },
        "user_id": "usr-123"
    }
    processed = redact_sensitive_processor(None, "info", event_dict)
    assert processed["authorization"] == "[REDACTED]"
    assert processed["token"] == "[REDACTED]"
    assert processed["headers"]["api_key"] == "[REDACTED]"
    assert processed["headers"]["safe_header"] == "application/json"
    assert processed["user_id"] == "usr-123"
