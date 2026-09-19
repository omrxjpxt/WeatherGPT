import time
import uuid
from contextlib import asynccontextmanager
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.rate_limiter import rate_limiter
from app.api.routes import health, trips, scenarios, weather, alerts, assistant, hazards, users

logger = structlog.get_logger("weathergpt.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield


app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    lifespan=lifespan,
)

RATE_LIMITED_PREFIXES = (
    "/api/v1/trips/analyze",
    "/api/v1/assistant/",
    "/api/v1/weather/",
)


class RequestCorrelationAndRateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Request ID Correlation
        req_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=req_id)

        # 2. Abuse Protection / Rate Limiting for expensive endpoints
        if request.method != "OPTIONS" and any(
            request.url.path.startswith(prefix) for prefix in RATE_LIMITED_PREFIXES
        ):
            is_limited, retry_after = rate_limiter.is_rate_limited(request)
            if is_limited:
                logger.warning(
                    "Rate limit exceeded",
                    path=request.url.path,
                    method=request.method,
                    retry_after=retry_after,
                )
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Please try again later."},
                    headers={"Retry-After": str(retry_after), "X-Request-Id": req_id},
                )

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            response.headers["X-Request-Id"] = req_id

            logger.info(
                "Request completed",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            return response
        except Exception as e:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "Request failed with unhandled exception",
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
                error=str(e),
            )
            raise


# Add inner correlation and rate limit middleware
app.add_middleware(RequestCorrelationAndRateLimitMiddleware)

# CORS configuration (outermost middleware)
cors_origins = list(settings.cors_origins)
if settings.is_production:
    cors_origins = [o for o in cors_origins if o != "*"]
else:
    for dev_origin in (
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
    ):
        if dev_origin not in cors_origins:
            cors_origins.append(dev_origin)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    req_id = request.headers.get("X-Request-Id") or ""
    headers = dict(exc.headers or {})
    if req_id:
        headers["X-Request-Id"] = req_id
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    req_id = request.headers.get("X-Request-Id") or "unknown"
    logger.error("Unhandled global exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred. Please try again later.",
            "requestId": req_id,
        },
        headers={"X-Request-Id": req_id},
    )


app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(trips.router, prefix="/api/v1/trips", tags=["Trips"])
app.include_router(scenarios.router, prefix="/api/v1/scenarios", tags=["Scenarios"])
app.include_router(weather.router, prefix="/api/v1/weather", tags=["Weather"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(assistant.router, prefix="/api/v1/assistant", tags=["Assistant"])
app.include_router(hazards.router, prefix="/api/v1/hazards", tags=["hazards"])


@app.get("/")
async def root():
    return {
        "message": "Welcome to WeatherGPT API. See /api/v1/health for status or /docs for API documentation."
    }
