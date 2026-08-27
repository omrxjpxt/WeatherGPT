from google.cloud import firestore
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

def get_firestore_client() -> firestore.AsyncClient | None:
    if not settings.firestore_project_id:
        logger.warning("Firestore project ID not set. Running in MEMORY MODE.")
        return None
    try:
        return firestore.AsyncClient(project=settings.firestore_project_id)
    except Exception as e:
        logger.warning("Failed to initialize Firestore. Running in MEMORY MODE.", error=str(e))
        return None
