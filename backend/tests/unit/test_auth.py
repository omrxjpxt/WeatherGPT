import pytest
from fastapi import HTTPException
from app.api.auth import get_authenticated_user, get_optional_current_user, get_current_user


class DummyRequest:
    def __init__(self, headers=None):
        self.headers = headers or {}


@pytest.mark.asyncio
async def test_auth_no_token_raises_401():
    req = DummyRequest(headers={})
    with pytest.raises(HTTPException) as exc_info:
        await get_authenticated_user(req)
    assert exc_info.value.status_code == 401
    assert "Missing Authorization header" in exc_info.value.detail


@pytest.mark.asyncio
async def test_auth_invalid_scheme_raises_401():
    req = DummyRequest(headers={"Authorization": "Basic 12345"})
    with pytest.raises(HTTPException) as exc_info:
        await get_authenticated_user(req)
    assert exc_info.value.status_code == 401
    assert "must be Bearer" in exc_info.value.detail


@pytest.mark.asyncio
async def test_auth_with_mock_token():
    req = DummyRequest(headers={"Authorization": "Bearer test-token"})
    user = await get_authenticated_user(req)
    assert user is not None
    assert user["uid"] == "test-user-id"


@pytest.mark.asyncio
async def test_auth_with_dynamic_mock_user_token():
    req = DummyRequest(headers={"Authorization": "Bearer mock-user-om"})
    user = await get_authenticated_user(req)
    assert user is not None
    assert user["uid"] == "mock-user-om"


@pytest.mark.asyncio
async def test_auth_expired_token_raises_401():
    req = DummyRequest(headers={"Authorization": "Bearer expired-token"})
    with pytest.raises(HTTPException) as exc_info:
        await get_authenticated_user(req)
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_auth_malformed_token_raises_401():
    req = DummyRequest(headers={"Authorization": "Bearer malformed-token"})
    with pytest.raises(HTTPException) as exc_info:
        await get_authenticated_user(req)
    assert exc_info.value.status_code == 401
    assert "malformed" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_optional_auth_guest():
    req = DummyRequest(headers={})
    user = await get_optional_current_user(req)
    assert user is None


@pytest.mark.asyncio
async def test_optional_auth_authenticated():
    req = DummyRequest(headers={"Authorization": "Bearer test-token"})
    user = await get_optional_current_user(req)
    assert user is not None
    assert user["uid"] == "test-user-id"
