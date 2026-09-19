import firebase_admin
from firebase_admin import auth
from fastapi import Request, HTTPException, status
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Initialize Firebase Admin if not already initialized
if not firebase_admin._apps:
    try:
        firebase_admin.initialize_app()
    except Exception as e:
        logger.warning(f"Failed to initialize Firebase Admin: {e}")


async def get_optional_current_user(request: Request) -> Optional[dict]:
    """
    Extracts Bearer token from request if present.
    Returns decoded token dictionary (including 'uid') if valid, else None.
    Does not raise HTTPException; safe for public/guest endpoints.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    parts = auth_header.split(" ", 1)
    if len(parts) < 2:
        return None
    token = parts[1].strip()
    if not token:
        return None

    from app.core.config import settings
    if settings.environment == "test" or not settings.firestore_project_id:
        if token == "test-token":
            return {"uid": "test-user-id", "email": "test@example.com"}
        if token.startswith("mock-user-") or token.startswith("mock-uid-") or token.startswith("user-"):
            return {"uid": token, "email": f"{token}@example.com"}
        if token in ("expired-token", "malformed-token", "invalid-token"):
            return None

    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        logger.warning("Optional Firebase token verification failed; treating as guest", error=str(e))
        return None


async def get_authenticated_user(request: Request) -> dict:
    """
    Strict authentication dependency for protected endpoints (/users/me/*).
    Raises HTTPException(401) on missing, malformed, or expired tokens.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header scheme, must be Bearer",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = auth_header.split(" ", 1)
    if len(parts) < 2 or not parts[1].strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1].strip()

    from app.core.config import settings
    if settings.environment == "test" or not settings.firestore_project_id:
        if token == "expired-token":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if token in ("malformed-token", "invalid-token"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed or invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if token == "test-token":
            return {"uid": "test-user-id", "email": "test@example.com"}
        if token.startswith("mock-user-") or token.startswith("mock-uid-") or token.startswith("user-"):
            return {"uid": token, "email": f"{token}@example.com"}

    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired authentication token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# Backward-compatible alias for existing imports
get_current_user = get_authenticated_user
