from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.routes import health, trips, scenarios, weather, alerts, assistant, hazards

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    yield

app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(trips.router, prefix="/api/v1/trips", tags=["Trips"])
app.include_router(scenarios.router, prefix="/api/v1/scenarios", tags=["Scenarios"])
app.include_router(weather.router, prefix="/api/v1/weather", tags=["Weather"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])
app.include_router(assistant.router, prefix="/api/v1/assistant", tags=["Assistant"])
app.include_router(hazards.router, prefix="/api/v1/hazards", tags=["hazards"])

@app.get("/")
async def root():
    return {"message": "Welcome to WeatherGPT API. See /api/v1/health for status or /docs for API documentation."}
