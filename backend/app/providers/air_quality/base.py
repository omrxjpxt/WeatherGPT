from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class AirQualityPoint(BaseModel):
    time: datetime
    pm2_5: float  # µg/m³
    pm10: float  # µg/m³
    aqi: int  # 0-500 US EPA scale
    category: str  # "Good" | "Moderate" | "Unhealthy for Sensitive Groups" | "Unhealthy" | "Very Unhealthy" | "Severe" | "Hazardous"
    source_name: str
    is_stale: bool = False
    observation_time: Optional[datetime] = None


class AirQualitySnapshot(BaseModel):
    aqi: int
    pm2_5: float
    pm10: float
    category: str
    source_name: str
    is_available: bool = True
    is_stale: bool = False
    observation_time: Optional[datetime] = None
    provenance: str = "live_provider"


def calculate_us_aqi_from_pm25(pm25: float) -> int:
    """
    Standard US EPA piecewise linear formula for converting PM2.5 (µg/m³) to AQI.
    Reference: EPA-454/B-18-007
    """
    if pm25 < 0:
        return 0

    # (C_low, C_high, I_low, I_high)
    breakpoints = [
        (0.0, 12.0, 0, 50),
        (12.1, 35.4, 51, 100),
        (35.5, 55.4, 101, 150),
        (55.5, 150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500),
    ]

    for c_low, c_high, i_low, i_high in breakpoints:
        if c_low <= pm25 <= c_high:
            aqi = ((i_high - i_low) / (c_high - c_low)) * (pm25 - c_low) + i_low
            return round(aqi)

    if pm25 > 500.4:
        return 500

    return 0


def classify_aqi_category(aqi: int) -> str:
    """Categorizes EPA AQI score into standard advisory categories."""
    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Moderate"
    elif aqi <= 150:
        return "Unhealthy for Sensitive Groups"
    elif aqi <= 200:
        return "Unhealthy"
    elif aqi <= 300:
        return "Very Unhealthy"
    elif aqi <= 400:
        return "Severe"
    else:
        return "Hazardous"


class AirQualityProvider(ABC):
    """Abstract interface for external Air Quality telemetry providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifier for the air quality provider."""
        pass

    @abstractmethod
    async def get_air_quality(
        self, lat: float, lng: float, start_time: datetime, hours: int = 4
    ) -> Optional[list[AirQualityPoint]]:
        """
        Retrieves hourly air quality telemetry for the given coordinates.
        Returns None on provider outage or failure (truthful degradation).
        """
        pass
