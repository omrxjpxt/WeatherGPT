from datetime import datetime, timezone
from fastapi import APIRouter, Response, status
from app.core.config import settings

router = APIRouter()

@router.get("/health", response_model=dict)
async def health_check():
    return {
        "status": "ok",
        "service": settings.project_name,
        "version": settings.version,
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/ready", response_model=dict)
@router.get("/health/ready", response_model=dict)
async def readiness_probe(response: Response):
    from app.api.dependencies import weather_provider, geocoding_provider, firestore_client
    from app.core.http import HttpClientManager

    checks = {}
    is_ready = True

    # 1. Config Check
    checks["config"] = "ok"

    # 2. Weather Provider Check
    if weather_provider:
        checks["weather_provider"] = {
            "status": "ok",
            "name": weather_provider.provider_name,
        }
    else:
        checks["weather_provider"] = {"status": "unconfigured"}
        if settings.is_production:
            is_ready = False

    # 3. Geocoding Provider Check
    if geocoding_provider:
        checks["geocoding_provider"] = {
            "status": "ok",
            "name": geocoding_provider.provider_name,
        }
    else:
        checks["geocoding_provider"] = {"status": "unconfigured"}
        if settings.is_production:
            is_ready = False

    # 4. Shared HTTP Connection Pool
    client = HttpClientManager.get_client()
    checks["http_pool"] = {
        "status": "ok" if (client is not None and not client.is_closed) else "idle"
    }

    # 5. Database Status
    if firestore_client is not None:
        checks["database"] = {"status": "connected", "type": "firestore"}
    elif settings.is_production:
        checks["database"] = {"status": "disconnected"}
        is_ready = False
    else:
        checks["database"] = {"status": "ok", "type": "memory_mock"}

    overall_status = "ready" if is_ready else "not_ready"
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": overall_status,
        "service": settings.project_name,
        "version": settings.version,
        "environment": settings.environment,
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

