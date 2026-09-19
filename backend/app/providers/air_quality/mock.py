from datetime import datetime, timezone, timedelta
from typing import Optional
from app.providers.air_quality.base import (
    AirQualityProvider,
    AirQualityPoint,
    classify_aqi_category,
)


class MockAirQualityProvider(AirQualityProvider):
    """
    Deterministic mock air quality provider for test suites and offline development.
    Explicitly tags points as mock_test source.
    """

    def __init__(
        self,
        default_aqi: int = 180,
        default_pm25: float = 95.0,
        default_pm10: float = 160.0,
        simulate_failure: bool = False,
        simulate_stale: bool = False,
    ):
        self.default_aqi = default_aqi
        self.default_pm25 = default_pm25
        self.default_pm10 = default_pm10
        self.simulate_failure = simulate_failure
        self.simulate_stale = simulate_stale

    @property
    def provider_name(self) -> str:
        return "mock"

    async def get_air_quality(
        self, lat: float, lng: float, start_time: datetime, hours: int = 4
    ) -> Optional[list[AirQualityPoint]]:
        if self.simulate_failure:
            return None

        points: list[AirQualityPoint] = []
        now = datetime.now(timezone.utc)
        obs_time = now - timedelta(hours=8) if self.simulate_stale else now

        for h in range(hours):
            point_time = start_time + timedelta(hours=h)
            points.append(
                AirQualityPoint(
                    time=point_time,
                    pm2_5=self.default_pm25,
                    pm10=self.default_pm10,
                    aqi=self.default_aqi,
                    category=classify_aqi_category(self.default_aqi),
                    source_name="mock (deterministic)",
                    is_stale=self.simulate_stale,
                    observation_time=obs_time,
                )
            )

        return points
