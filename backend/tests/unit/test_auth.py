import pytest
from fastapi import Request
from app.api.auth import get_current_user

@pytest.mark.asyncio
async def test_auth_no_token():
    class DummyRequest:
        headers = {}
    
    # In test environment, config should bypass and return mock user
    user = await get_current_user(DummyRequest())
    assert user is not None
    assert user["uid"] == "test-user-id"

@pytest.mark.asyncio
async def test_auth_with_mock_token():
    class DummyRequest:
        headers = {"Authorization": "Bearer test-token"}
    
    user = await get_current_user(DummyRequest())
    assert user is not None
    assert user["uid"] == "test-user-id"
