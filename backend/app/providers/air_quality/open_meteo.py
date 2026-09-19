from datetime import datetime, timezone
import logging
from typing import Optional
import httpx
from app.providers.air_quality.base import (
    AirQualityProvider,
    AirQualityPoint,
    calculate_us_aqi_from_pm25,
    classify_aqi_category,
)

logger = logging.getLogger(__name__)

OPEN_METEO_AQI_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"


class OpenMeteoAirQualityProvider(AirQualityProvider):
    """
    Open-Meteo Air Quality API client.
    Powered by Copernicus Atmosphere Monitoring Service (CAMS).
    Provides hourly PM2.5, PM10, and US AQI.
    """

    def __init__(
        self,
        timeout: float = 6.0,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        self.timeout = timeout
        self._external_client = http_client

    @property
    def provider_name(self) -> str:
        return "open-meteo"

    async def get_air_quality(
        self, lat: float, lng: float, start_time: datetime, hours: int = 4
    ) -> Optional[list[AirQualityPoint]]:
        params = {
            "latitude": lat,
            "longitude": lng,
            "hourly": "pm10,pm2_5,us_aqi",
            "forecast_days": 2,
            "timezone": "auto",
        }

        try:
            if self._external_client:
                response = await self._external_client.get(
                    OPEN_METEO_AQI_URL,
                    params=params,
                    timeout=self.timeout,
                )
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        OPEN_METEO_AQI_URL,
                        params=params,
                        timeout=self.timeout,
                    )

            if response.status_code != 200:
                logger.warning(
                    f"Open-Meteo Air Quality returned status {response.status_code} for ({lat}, {lng})"
                )
                return None

            data = response.json()
            hourly = data.get("hourly")
            if not hourly:
                return None

            times = hourly.get("time", [])
            pm25_list = hourly.get("pm2_5", [])
            pm10_list = hourly.get("pm10", [])
            us_aqi_list = hourly.get("us_aqi", [])

            if not times:
                return None

            now = datetime.now(timezone.utc)
            points: list[AirQualityPoint] = []

            for i, time_str in enumerate(times):
                try:
                    point_time = datetime.fromisoformat(time_str)
                    if point_time.tzinfo is None:
                        point_time = point_time.replace(tzinfo=timezone.utc)

                    # Filter for relevant window
                    if point_time < start_time:
                        continue
                    if len(points) >= hours:
                        break

                    pm25_val = float(pm25_list[i]) if i < len(pm25_list) and pm25_list[i] is not None else 0.0
                    pm10_val = float(pm10_list[i]) if i < len(pm10_list) and pm10_list[i] is not None else 0.0
                    raw_aqi = int(us_aqi_list[i]) if i < len(us_aqi_list) and us_aqi_list[i] is not None else 0

                    # PM2.5 precedence harmonization:
                    # Compute EPA AQI equivalent from PM2.5 and take the max with reported US AQI
                    pm25_derived_aqi = calculate_us_aqi_from_pm25(pm25_val)
                    effective_aqi = max(raw_aqi, pm25_derived_aqi)

                    # Staleness check: if observation/forecast delta > 6 hours from current time
                    is_stale = abs((now - point_time).total_seconds()) > (6 * 3600)

                    points.append(
                        AirQualityPoint(
                            time=point_time,
                            pm2_5=round(pm25_val, 1),
                            pm10=round(pm10_val, 1),
                            aqi=effective_aqi,
                            category=classify_aqi_category(effective_aqi),
                            source_name="open-meteo (CAMS)",
                            is_stale=is_stale,
                            observation_time=now,
                        )
                    )
                except (ValueError, IndexError):
                    continue

            return points if points else None

        except Exception as e:
            logger.warning(f"Open-Meteo Air Quality fetch failed: {e}")
            return None
