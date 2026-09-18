import firebase_admin
from firebase_admin import auth, credentials
from fastapi import Request
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)

# Initialize Firebase Admin if not already initialized
if not firebase_admin._apps:
    try:
        # Default application credentials or initialized dynamically
        firebase_admin.initialize_app()
    except Exception as e:
        logger.warning(f"Failed to initialize Firebase Admin: {e}")

async def get_current_user(request: Request) -> Optional[dict]:
    """
    Extracts Bearer token from request and verifies it using Firebase Admin.
    Returns decoded token dictionary (which includes 'uid') if valid, else None.
    If auth is disabled (testing/memory mode), can return a dummy user.
    """
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        # Check settings for test bypass
        from app.core.config import settings
        if settings.environment == "test" or not settings.firestore_project_id:
            return {"uid": "test-user-id", "email": "test@example.com"}
        return None
    
    token = auth_header.split(" ")[1]
    
    from app.core.config import settings
    if settings.environment == "test" or not settings.firestore_project_id:
         # In memory mode/test, accept dummy tokens or return dummy user regardless
         if token == "test-token":
             return {"uid": "test-user-id", "email": "test@example.com"}

    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {e}")
        return None
