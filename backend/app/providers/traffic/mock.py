import asyncio
from typing import List
from app.providers.traffic.base import TrafficProvider
from app.decision_engine.normalized_models import NormalizedRouteSegment

class MockTrafficProvider(TrafficProvider):
    async def get_traffic_factors(self, segments: List[NormalizedRouteSegment]) -> List[float]:
        await asyncio.sleep(0.1)
        # Mock traffic: slightly congested in the middle segments
        factors = []
        for i, _ in enumerate(segments):
            if 1 < i < 4:
                factors.append(1.5) # 50% slower
            else:
                factors.append(1.0)
        return factors
