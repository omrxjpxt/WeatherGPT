import pytest
from datetime import datetime, timezone, timedelta
from app.providers.transit.dmrc_gtfs import DmrcMetroProvider
from app.models.enums import TransportMode, RouteStatus


@pytest.mark.asyncio
async def test_station_graph_construction():
    provider = DmrcMetroProvider()
    assert len(provider.stations) >= 40
    assert "rajiv_chowk" in provider.stations
    assert "kashmere_gate" in provider.stations
    assert "botanical_garden" in provider.stations
    assert "huda_city_centre" in provider.stations
    assert provider.route_status == RouteStatus.live


@pytest.mark.asyncio
async def test_direct_route_same_line():
    provider = DmrcMetroProvider()
    # Rajiv Chowk (28.6328, 77.2195) to Kashmere Gate (28.6675, 77.2285) on Yellow Line
    routes = await provider.get_route(
        origin_lat=28.6328, origin_lng=77.2195,
        dest_lat=28.6675, dest_lng=77.2285,
        mode=TransportMode.metro
    )
    
    assert len(routes) == 1
    r = routes[0]
    assert r.total_distance_km > 0
    assert r.total_duration.total_seconds() > 0
    assert len(r.segments) >= 2  # Access + Rail leg + Egress


@pytest.mark.asyncio
async def test_interchange_routing_multi_line():
    provider = DmrcMetroProvider()
    # Noida Sector 62 (Blue Line) to Millennium City Centre Gurgaon (Yellow Line)
    # Origin: Noida Sec 62 (28.6275, 77.3615)
    # Destination: Gurgaon MCC (28.4593, 77.0725)
    routes = await provider.get_route(
        origin_lat=28.6275, origin_lng=77.3615,
        dest_lat=28.4593, dest_lng=77.0725,
        mode=TransportMode.metro
    )
    
    assert len(routes) == 1
    r = routes[0]
    # Realistic duration for Noida to Gurgaon metro is between 50 and 100 minutes
    duration_mins = r.total_duration.total_seconds() / 60.0
    assert 50 <= duration_mins <= 100
    assert len(r.segments) >= 15 # Multiple transit station segments


@pytest.mark.asyncio
async def test_unsupported_station_out_of_range_no_route():
    provider = DmrcMetroProvider()
    # Jaipur coordinates (far out of Delhi-NCR range, >200km)
    routes = await provider.get_route(
        origin_lat=26.9124, origin_lng=75.7873,
        dest_lat=28.6328, dest_lng=77.2195,
        mode=TransportMode.metro
    )
    # Must return typed empty list rather than inventing a synthetic route
    assert routes == []


@pytest.mark.asyncio
async def test_deterministic_repeated_routing_10x():
    provider = DmrcMetroProvider()
    origin_lat, origin_lng = 28.6275, 77.3615
    dest_lat, dest_lng = 28.5355, 77.2065 # Hauz Khas
    
    first_run = await provider.get_route(origin_lat, origin_lng, dest_lat, dest_lng, TransportMode.metro)
    assert len(first_run) == 1
    first_route = first_run[0]
    
    for _ in range(10):
        subsequent_run = await provider.get_route(origin_lat, origin_lng, dest_lat, dest_lng, TransportMode.metro)
        assert len(subsequent_run) == 1
        subsequent_route = subsequent_run[0]
        assert subsequent_route.total_duration == first_route.total_duration
        assert subsequent_route.total_distance_km == first_route.total_distance_km
        assert len(subsequent_route.segments) == len(first_route.segments)
        for s1, s2 in zip(first_route.segments, subsequent_route.segments):
            assert s1.start_lat == s2.start_lat
            assert s1.start_lng == s2.start_lng
            assert s1.estimated_duration == s2.estimated_duration


def test_provenance_and_version_metadata():
    provider = DmrcMetroProvider()
    meta = provider.metadata
    assert "agency" in meta
    assert "source" in meta
    assert "version" in meta
    assert "delhi.transportstack.in" in meta.get("source", "")
