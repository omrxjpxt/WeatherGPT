import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.providers.alerts.sachet_cap import (
    NdmaSachetAlertProvider,
    _parse_cap_severity,
    _point_in_polygon,
)
from app.models.enums import AlertSeverity, AlertSourceClass
from app.decision_engine.normalized_models import NormalizedAlert


SAMPLE_CAP_12_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>NDMA-SACHET-DELHI-2026-001</identifier>
  <sender>ndma.gov.in</sender>
  <sent>2026-09-19T20:00:00+05:30</sent>
  <status>Actual</status>
  <msgType>Alert</msgType>
  <scope>Public</scope>
  <info>
    <category>Met</category>
    <event>Severe Flash Flood and Heavy Inundation</event>
    <urgency>Immediate</urgency>
    <severity>Extreme</severity>
    <certainty>Observed</certainty>
    <headline>Flash flood inundation warning for Delhi Central and South districts</headline>
    <description>Severe waterlogging observed at major underpasses and arterial roads due to heavy downpour.</description>
    <instruction>Avoid low-lying underpasses including Minto Bridge and Pul Prahlad Pur. Seek high ground.</instruction>
    <effective>2026-09-19T20:00:00+05:30</effective>
    <expires>2026-09-20T02:00:00+05:30</expires>
    <area>
      <areaDesc>districts of New Delhi, Central Delhi, South Delhi</areaDesc>
      <polygon>28.50,77.10 28.70,77.10 28.70,77.30 28.50,77.30 28.50,77.10</polygon>
    </area>
  </info>
</alert>
"""

SAMPLE_RSS_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>NDMA SACHET Delhi Bulletins</title>
    <link>https://sachet.ndma.gov.in</link>
    <item>
      <title>Heavy Rainfall Alert for Delhi NCR</title>
      <category>Met</category>
      <link>https://sachet.ndma.gov.in/cap_public_website/FetchXMLFile?id=NDMA-SACHET-DELHI-2026-001</link>
      <guid>NDMA-SACHET-DELHI-2026-001</guid>
      <pubDate>Sat, 19 Sep 2026 20:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""

MALICIOUS_XXE_XML = b"""<?xml version="1.0" encoding="ISO-8859-1"?>
<!DOCTYPE alert [
  <!ELEMENT alert ANY >
  <!ENTITY xxe SYSTEM "file:///etc/passwd" >]>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>&xxe;</identifier>
  <info>
    <headline>&xxe;</headline>
    <event>XXE Exploit Attempt</event>
    <severity>Extreme</severity>
  </info>
</alert>
"""


@pytest.mark.asyncio
async def test_valid_cap_xml_parsing():
    provider = NdmaSachetAlertProvider()
    fallback_data = {"guid": "fallback-guid", "title": "Fallback Title"}
    
    alert = provider.parse_cap_xml(SAMPLE_CAP_12_XML, fallback_data)
    
    assert alert.id == "NDMA-SACHET-DELHI-2026-001"
    assert alert.headline == "Flash flood inundation warning for Delhi Central and South districts"
    assert alert.event == "Severe Flash Flood and Heavy Inundation"
    assert alert.urgency == "Immediate"
    assert alert.certainty == "Observed"
    assert alert.severity == AlertSeverity.emergency
    assert alert.source_class == AlertSourceClass.authoritative
    assert alert.is_override_eligible is True
    assert "Minto Bridge" in alert.action
    assert len(alert.affected_areas_polygon) == 5
    assert len(alert.affected_districts) >= 2


@pytest.mark.asyncio
async def test_provenance_and_authority():
    provider = NdmaSachetAlertProvider()
    assert provider.provider_name == "NDMA SACHET (Government of India)"
    assert provider.provider_class == AlertSourceClass.authoritative


@pytest.mark.asyncio
async def test_session_client_preserves_cookies():
    provider = NdmaSachetAlertProvider()
    client1 = await provider._get_client()
    client2 = await provider._get_client()
    
    # Must reuse the same persistent httpx.AsyncClient session
    assert client1 is client2
    assert isinstance(client1.cookies, httpx.Cookies)
    await provider.close()


@pytest.mark.asyncio
async def test_etag_and_304_not_modified():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    
    # 1st call returns 200 OK with ETag "tag-123"
    resp_200 = MagicMock(status_code=200, content=SAMPLE_RSS_FEED)
    resp_200.headers = {"etag": '"tag-123"'}
    
    # Detail call returns CAP 1.2 XML
    detail_resp = MagicMock(status_code=200, content=SAMPLE_CAP_12_XML)
    detail_resp.headers = {}
    
    mock_client.get.side_effect = [resp_200, detail_resp]
    
    provider = NdmaSachetAlertProvider(client=mock_client, cache_ttl_seconds=0)
    alerts = await provider.fetch_feed_alerts()
    assert len(alerts) == 1
    assert provider._etag == '"tag-123"'
    
    # 2nd call returns 304 Not Modified
    resp_304 = MagicMock(status_code=304, content=b"")
    resp_304.headers = {}
    mock_client.get.side_effect = [resp_304]
    
    cached_alerts = await provider.fetch_feed_alerts()
    assert len(cached_alerts) == 1
    assert cached_alerts[0].id == "NDMA-SACHET-DELHI-2026-001"


@pytest.mark.asyncio
async def test_malformed_xml_handling():
    provider = NdmaSachetAlertProvider()
    fallback_data = {"guid": "malformed-fallback", "title": "Malformed Item Alert", "pubDate": datetime.now(timezone.utc)}
    
    # Corrupted binary data
    corrupted_xml = b"<<<not_valid_xml???>>>"
    alert = provider.parse_cap_xml(corrupted_xml, fallback_data)
    
    # Should fall back cleanly without crashing
    assert alert.id == "malformed-fallback"
    assert alert.headline == "Malformed Item Alert"


@pytest.mark.asyncio
async def test_xxe_defense():
    """defusedxml must defuse external entity injection attempts."""
    provider = NdmaSachetAlertProvider()
    fallback_data = {"guid": "xxe-test", "title": "XXE Attempt"}
    
    alert = provider.parse_cap_xml(MALICIOUS_XXE_XML, fallback_data)
    
    # Ensure external entity is not expanded into sensitive system data
    assert "/bin/bash" not in alert.headline
    assert "root:x" not in alert.id


@pytest.mark.asyncio
async def test_timeout_and_network_failure_truthful_degradation():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.side_effect = httpx.TimeoutException("Government gateway timed out")
    
    provider = NdmaSachetAlertProvider(client=mock_client, cache_ttl_seconds=0)
    alerts = await provider.fetch_feed_alerts()
    
    # Must return empty list, never fabricated alerts
    assert alerts == []


@pytest.mark.asyncio
async def test_cached_alert_ttl_behavior():
    now = datetime.now(timezone.utc)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    provider = NdmaSachetAlertProvider(client=mock_client, cache_ttl_seconds=300)
    
    # Seed cache
    fake_alert = NormalizedAlert(
        id="cached-1",
        source_name=provider.provider_name,
        source_class=provider.provider_class,
        severity=AlertSeverity.warning,
        affected_areas_polygon=[],
        issued_at=now,
        expires_at=now + timedelta(hours=2),
        action="Stay indoors",
        headline="Cached Alert",
        event="Rain",
        urgency="Expected",
        certainty="Likely"
    )
    provider._cached_alerts = [fake_alert]
    provider._last_fetch_time = now - timedelta(seconds=60) # 60s ago < 300s TTL
    
    alerts = await provider.fetch_feed_alerts()
    assert len(alerts) == 1
    assert alerts[0].id == "cached-1"
    # No HTTP request made because cache is within TTL
    mock_client.get.assert_not_called()


@pytest.mark.asyncio
async def test_spatial_filtering_within_and_outside_polygon():
    provider = NdmaSachetAlertProvider()
    now = datetime.now(timezone.utc)
    
    # Polygon around Central/South Delhi: lat [28.50, 28.70], lng [77.10, 77.30]
    alert = NormalizedAlert(
        id="geo-alert-1",
        source_name=provider.provider_name,
        source_class=provider.provider_class,
        severity=AlertSeverity.warning,
        affected_areas_polygon=[
            [28.50, 77.10],
            [28.70, 77.10],
            [28.70, 77.30],
            [28.50, 77.30],
            [28.50, 77.10]
        ],
        issued_at=now,
        expires_at=now + timedelta(hours=3),
        action="Avoid underpasses",
        headline="Delhi Alert",
        event="Rain",
        urgency="Expected",
        certainty="Likely"
    )
    provider._cached_alerts = [alert]
    provider._last_fetch_time = now
    
    # Point inside (Connaught Place: 28.63, 77.22)
    active_inside = await provider.get_active_alerts(28.63, 77.22)
    assert len(active_inside) == 1
    assert active_inside[0].id == "geo-alert-1"
    
    # Point outside (Mumbai: 19.0760, 72.8777)
    active_outside = await provider.get_active_alerts(19.0760, 72.8777)
    assert len(active_outside) == 0


@pytest.mark.asyncio
async def test_http_403_waf_challenge_handling():
    """When government feed returns 403 WAF challenge, provider must degrade gracefully."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 403
    mock_client.get.return_value = mock_response

    provider = NdmaSachetAlertProvider(client=mock_client, cache_ttl_seconds=0)
    alerts = await provider.fetch_feed_alerts()

    assert alerts == []
    assert provider.provider_status == "waf_challenge"
    assert provider._last_status_code == 403

