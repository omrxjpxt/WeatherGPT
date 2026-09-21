import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
import defusedxml.ElementTree as ET
import httpx

from app.providers.alerts.base import AlertProvider
from app.models.enums import AlertSeverity, AlertSourceClass
from app.decision_engine.normalized_models import NormalizedAlert
from app.core.config import settings

logger = logging.getLogger(__name__)

# Standard Delhi-NCR Bounding Polygon for regional alerts without explicit geometry
DEFAULT_DELHI_NCR_POLYGON = [
    [28.40, 76.84],
    [28.88, 76.84],
    [28.88, 77.40],
    [28.40, 77.40],
]

CAP_NS = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}

def _parse_cap_severity(severity_str: Optional[str]) -> AlertSeverity:
    if not severity_str:
        return AlertSeverity.advisory
    val = severity_str.strip().lower()
    if val == "extreme":
        return AlertSeverity.emergency
    elif val == "severe":
        return AlertSeverity.warning
    elif val == "moderate":
        return AlertSeverity.watch
    elif val == "minor":
        return AlertSeverity.advisory
    return AlertSeverity.advisory

def _parse_cap_datetime(dt_str: Optional[str]) -> Optional[datetime]:
    if not dt_str:
        return None
    try:
        # ISO-8601 parsing, e.g. 2026-09-19T22:23:00+05:30
        return datetime.fromisoformat(dt_str)
    except Exception:
        try:
            return datetime.strptime(dt_str.strip(), "%a, %d %b %Y %H:%M:%S %Z").replace(tzinfo=timezone.utc)
        except Exception:
            return None

def _point_in_polygon(lat: float, lng: float, polygon: List[List[float]]) -> bool:
    """Standard ray-casting algorithm for 2D polygon inclusion."""
    if not polygon or len(polygon) < 3:
        return True # Permissive if geometry is not a full polygon
    n = len(polygon)
    inside = False
    p1x, p1y = polygon[0][1], polygon[0][0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n][1], polygon[i % n][0]
        if min(p1y, p2y) < lat <= max(p1y, p2y):
            if lng <= max(p1x, p2x):
                if p1y != p2y:
                    xinters = (lat - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                if p1x == p2x or lng <= xinters:
                    inside = not inside
        p1x, p1y = p2x, p2y
    return inside


class NdmaSachetAlertProvider(AlertProvider):
    """
    Official Government of India Emergency Alert Provider consuming
    National Disaster Management Authority (NDMA) SACHET CAP 1.2 Feeds.

    Aggregates official bulletins from IMD (India Meteorological Department)
    and CWC (Central Water Commission).
    """

    def __init__(
        self,
        feed_url: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        cache_ttl_seconds: Optional[int] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.feed_url = feed_url or settings.sachet_feed_url
        self.timeout_seconds = timeout_seconds or settings.sachet_timeout_seconds
        self.cache_ttl_seconds = cache_ttl_seconds or settings.sachet_cache_ttl_seconds
        # Persistent httpx client with cookie jar to preserve government gateway session
        self._external_client = client
        self._client: Optional[httpx.AsyncClient] = client
        self._etag: Optional[str] = None
        self._cached_alerts: List[NormalizedAlert] = []
        self._last_fetch_time: Optional[datetime] = None
        self._last_status: str = "ok"
        self._last_status_code: Optional[int] = None

    @property
    def provider_name(self) -> str:
        return "NDMA SACHET (Government of India)"

    @property
    def provider_class(self) -> str:
        return AlertSourceClass.authoritative

    @property
    def provider_status(self) -> str:
        return self._last_status

    async def _get_client(self) -> httpx.AsyncClient:
        if self._external_client is not None:
            return self._external_client
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout_seconds,
                follow_redirects=True,
                headers={
                    "User-Agent": "WeatherGPT-DisasterAlerts/1.0 (Mozilla/5.0; compatible; Delhi-NCR Travel Safety)",
                    "Accept": "application/rss+xml, text/xml, application/xml, */*",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._external_client:
            await self._client.aclose()
            self._client = None

    def parse_cap_xml(self, xml_content: bytes, fallback_item_data: dict) -> NormalizedAlert:
        """
        Parses a CAP 1.2 XML document using defusedxml.
        Returns a NormalizedAlert object.
        """
        try:
            root = ET.fromstring(xml_content)
        except Exception as e:
            logger.warning(f"Failed to parse CAP XML with defusedxml: {e}")
            return self._build_fallback_alert(fallback_item_data)

        # Handle namespace
        info = root.find("cap:info", CAP_NS)
        if info is None:
            info = root.find("info") # Namespace fallback

        identifier = root.findtext("cap:identifier", default="", namespaces=CAP_NS) or fallback_item_data.get("guid", "sachet-alert")
        headline = info.findtext("cap:headline", default="", namespaces=CAP_NS) if info is not None else ""
        if not headline:
            headline = fallback_item_data.get("title", "")

        event = info.findtext("cap:event", default="Weather Advisory", namespaces=CAP_NS) if info is not None else fallback_item_data.get("category", "Met")
        urgency = info.findtext("cap:urgency", default="Unknown", namespaces=CAP_NS) if info is not None else "Unknown"
        severity_raw = info.findtext("cap:severity", default="Moderate", namespaces=CAP_NS) if info is not None else "Moderate"
        certainty = info.findtext("cap:certainty", default="Unknown", namespaces=CAP_NS) if info is not None else "Unknown"
        desc = info.findtext("cap:description", default="", namespaces=CAP_NS) if info is not None else ""
        instruction = info.findtext("cap:instruction", default="", namespaces=CAP_NS) if info is not None else "Follow local authority guidelines."

        effective_str = info.findtext("cap:effective", default="", namespaces=CAP_NS) if info is not None else ""
        expires_str = info.findtext("cap:expires", default="", namespaces=CAP_NS) if info is not None else ""

        effective = _parse_cap_datetime(effective_str) or fallback_item_data.get("pubDate") or datetime.now(timezone.utc)
        expires = _parse_cap_datetime(expires_str)
        if not expires:
            expires = effective + timedelta(hours=6)

        # Extract area description and polygon
        area = info.find("cap:area", CAP_NS) if info is not None else None
        area_desc = area.findtext("cap:areaDesc", default="Delhi-NCR", namespaces=CAP_NS) if area is not None else "Delhi-NCR"
        
        polygon_coords: List[List[float]] = []
        if area is not None:
            polygon_str = area.findtext("cap:polygon", default="", namespaces=CAP_NS)
            if polygon_str:
                try:
                    for pt in polygon_str.strip().split():
                        parts = pt.split(",")
                        if len(parts) == 2:
                            polygon_coords.append([float(parts[0]), float(parts[1])])
                except Exception:
                    polygon_coords = []

        if not polygon_coords:
            polygon_coords = DEFAULT_DELHI_NCR_POLYGON

        # Parse districts
        districts = [d.strip() for d in area_desc.replace("districts of", "").replace("and", ",").split(",") if d.strip()]

        return NormalizedAlert(
            id=identifier,
            source_name=self.provider_name,
            source_class=self.provider_class,
            severity=_parse_cap_severity(severity_raw),
            affected_areas_polygon=polygon_coords,
            issued_at=effective,
            expires_at=expires,
            action=instruction or "Exercise caution while commuting.",
            source_url=fallback_item_data.get("link"),
            is_override_eligible=True,
            headline=headline,
            event=event,
            urgency=urgency,
            certainty=certainty,
            affected_districts=districts
        )

    def _build_fallback_alert(self, item_data: dict) -> NormalizedAlert:
        """Constructs an alert directly from RSS item if full CAP XML fetch fails."""
        now = datetime.now(timezone.utc)
        issued_at = item_data.get("pubDate") or now
        return NormalizedAlert(
            id=item_data.get("guid", f"sachet-{now.timestamp()}"),
            source_name=self.provider_name,
            source_class=self.provider_class,
            severity=AlertSeverity.warning if "rain" in item_data.get("title", "").lower() else AlertSeverity.watch,
            affected_areas_polygon=DEFAULT_DELHI_NCR_POLYGON,
            issued_at=issued_at,
            expires_at=issued_at + timedelta(hours=6),
            action="Follow IMD / NDMA travel advisories.",
            source_url=item_data.get("link"),
            is_override_eligible=True,
            headline=item_data.get("title", "Severe Weather Advisory"),
            event=item_data.get("category", "Met"),
            urgency="Expected",
            certainty="Observed",
            affected_districts=["Delhi", "NCT", "NCR"]
        )

    async def fetch_feed_alerts(self) -> List[NormalizedAlert]:
        """Fetches the RSS feed with ETag caching and extracts active alerts."""
        now = datetime.now(timezone.utc)

        # Check in-memory cache validity
        if (
            self._cached_alerts
            and self._last_fetch_time
            and (now - self._last_fetch_time).total_seconds() < self.cache_ttl_seconds
        ):
            logger.debug("Returning NDMA SACHET alerts from in-memory cache.")
            return self._cached_alerts

        client = await self._get_client()
        headers = {}
        if self._etag:
            headers["If-None-Match"] = self._etag

        try:
            response = await client.get(self.feed_url, headers=headers)
        except httpx.TimeoutException:
            self._last_status = "timeout"
            self._last_status_code = None
            logger.warning("Timeout connecting to NDMA SACHET feed. Returning cached/empty alerts.")
            return self._cached_alerts or []
        except Exception as e:
            self._last_status = "error"
            self._last_status_code = None
            logger.warning(f"Error connecting to NDMA SACHET feed: {e}. Returning cached/empty alerts.")
            return self._cached_alerts or []

        # Handle 304 Not Modified
        if response.status_code == 304:
            self._last_status = "ok"
            self._last_status_code = 304
            logger.debug("NDMA SACHET returned 304 Not Modified. Reusing cached alerts.")
            self._last_fetch_time = now
            return self._cached_alerts

        if response.status_code == 403:
            self._last_status = "waf_challenge"
            self._last_status_code = 403
            logger.warning(
                "NDMA SACHET feed returned HTTP 403 (Gateway/WAF challenge). "
                "Operating in truthful degraded alert state without fabricating emergency overrides."
            )
            return self._cached_alerts or []

        if response.status_code != 200:
            self._last_status = "degraded"
            self._last_status_code = response.status_code
            logger.warning(f"NDMA SACHET feed returned HTTP {response.status_code}. Reusing cached/empty alerts.")
            return self._cached_alerts or []

        self._last_status = "ok"
        self._last_status_code = 200

        # Update ETag and cache time
        self._etag = response.headers.get("etag") or response.headers.get("ETag")
        self._last_fetch_time = now

        # Parse RSS Feed safely
        try:
            rss_root = ET.fromstring(response.content)
        except Exception as e:
            logger.error(f"Malformed RSS feed XML from NDMA SACHET: {e}")
            return self._cached_alerts or []

        channel = rss_root.find("channel")
        if channel is None:
            return []

        items = channel.findall("item")
        if not items:
            self._cached_alerts = []
            return []

        parsed_alerts: List[NormalizedAlert] = []

        # Process the top 5 most recent alerts to prevent unbounded network fan-out
        for item in items[:5]:
            title = item.findtext("title", default="").strip()
            category = item.findtext("category", default="Met").strip()
            link = item.findtext("link", default="").strip()
            guid = item.findtext("guid", default="").strip()
            pub_date_str = item.findtext("pubDate", default="").strip()
            pub_date = _parse_cap_datetime(pub_date_str) or now

            item_data = {
                "title": title,
                "category": category,
                "link": link,
                "guid": guid or f"sachet-{now.timestamp()}",
                "pubDate": pub_date
            }

            # Attempt to fetch full CAP XML detail if link is present
            if link and "FetchXMLFile" in link:
                try:
                    detail_resp = await client.get(link, timeout=2.0)
                    if detail_resp.status_code == 200:
                        alert = self.parse_cap_xml(detail_resp.content, item_data)
                        parsed_alerts.append(alert)
                        continue
                except Exception as e:
                    logger.debug(f"Failed to fetch CAP XML detail for {guid}: {e}. Falling back to RSS item data.")

            # Fallback to RSS item data
            parsed_alerts.append(self._build_fallback_alert(item_data))

        self._cached_alerts = parsed_alerts
        return parsed_alerts

    async def get_active_alerts(self, lat: float, lng: float) -> List[NormalizedAlert]:
        """
        Fetches active alerts and filters by spatial relevance to the given coordinates.
        """
        all_alerts = await self.fetch_feed_alerts()
        relevant: List[NormalizedAlert] = []

        for alert in all_alerts:
            # Check expiration
            if alert.expires_at and alert.expires_at < datetime.now(timezone.utc):
                continue

            # Check spatial intersection
            if alert.affected_areas_polygon:
                if _point_in_polygon(lat, lng, alert.affected_areas_polygon):
                    relevant.append(alert)
            else:
                # Default regional match if coordinates fall within Delhi-NCR
                if 28.2 <= lat <= 29.0 and 76.6 <= lng <= 77.6:
                    relevant.append(alert)

        return relevant
