import math
from typing import List
from datetime import datetime, timezone, timedelta

from app.models.trip import TripRequest
from app.models.scenario import ScenarioResult
from app.models.enums import TripStatus
from app.services.trip_service import TripService


class ScenarioService:
    def __init__(self, trip_service: TripService):
        self.trip_service = trip_service

    async def evaluate_scenarios(self, request: TripRequest, departure_times: List[datetime]) -> List[ScenarioResult]:
        if not departure_times:
            return []

        # 1. Normalize all departure times to UTC to avoid tz-naive comparisons
        normalized_times = [
            t if t.tzinfo is not None else t.replace(tzinfo=timezone.utc)
            for t in departure_times
        ]

        sorted_times = sorted(normalized_times)
        earliest_time = sorted_times[0]
        latest_time = sorted_times[-1]

        # 2. Calculate forecast window to cover all requested departure times
        duration_hours = int(math.ceil((latest_time - earliest_time).total_seconds() / 3600)) + 12
        forecast_hours = max(24, min(72, duration_hours))

        # 3. Single corridor context resolution:
        # 1 geocoding pass, 1 routing pass, 1 weather forecast, 1 alert fetch, 1 AQI fetch, 1 hazard query
        base_request = request.model_copy(update={"departure_time": earliest_time})
        ctx = await self.trip_service.resolve_corridor_context(base_request, forecast_hours=forecast_hours)

        # 4. If weather is unavailable or routing failed, return degraded scenario results
        if not ctx.comparison.primary_timeline or not ctx.routes or ctx.routing_err is not None:
            status = TripStatus.weather_unavailable if not ctx.comparison.primary_timeline else TripStatus.routing_unavailable
            return [
                ScenarioResult(
                    departure_time=orig_time,
                    status=status,
                    risk=None,
                    estimated_duration=timedelta(0),
                    recommendation="Route guidance unavailable.",
                    changed_factors=[],
                )
                for orig_time in departure_times
            ]

        # 5. Evaluate all departure times in-memory using Decision Engine
        results = []
        for orig_time, norm_time in zip(departure_times, normalized_times):
            cand_request = request.model_copy(update={"departure_time": norm_time})

            evaluated_routes = []
            for r in ctx.routes:
                hazards = ctx.route_hazards.get(r.route_id, [])
                eval_r = self.trip_service.route_evaluator.evaluate_route(
                    route=r,
                    request=cand_request,
                    weather_timeline=ctx.comparison.primary_timeline,
                    hazards=hazards,
                    alerts=ctx.alerts,
                    traffic=None,
                    agreement_status=ctx.comparison.agreement_status.value,
                    air_quality_timeline=ctx.aqi_timeline,
                )
                evaluated_routes.append(eval_r)

            selected_route, _ = self.trip_service.route_evaluator.select_and_rank_routes(
                evaluated_routes,
                departure_time=norm_time,
                arrival_deadline=cand_request.arrival_deadline,
            )

            rec_body = (
                selected_route.evaluation.recommendation_body
                or selected_route.evaluation.recommendation_headline
                or "Route guidance unavailable."
            )

            results.append(ScenarioResult(
                departure_time=orig_time,
                status=TripStatus.success,
                risk=selected_route.risk,
                estimated_duration=selected_route.static_duration,
                recommendation=rec_body,
                changed_factors=[],
            ))

        return results

