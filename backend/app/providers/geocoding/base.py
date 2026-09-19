from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
import re
from typing import Any, Optional
from pydantic import BaseModel, Field


class GeocodingResultType(str, Enum):
    EXACT_LANDMARK = "exact_landmark"
    STREET = "street"
    SECTOR_NEIGHBORHOOD = "sector_neighborhood"
    CITY_LOCALITY = "city_locality"
    ADMINISTRATIVE = "administrative"
    POSTAL_CODE = "postal_code"
    COORDINATE = "coordinate"
    UNKNOWN = "unknown"


class GeocodingProvenance(str, Enum):
    LIVE_PROVIDER = "live_provider"
    OFFLINE_CURATED = "offline_curated"
    USER_COORDINATE = "user_coordinate"
    MOCK_TEST = "mock_test"


class GeocodingResult(BaseModel):
    query: str
    lat: float = Field(..., ge=-90.0, le=90.0)
    lng: float = Field(..., ge=-180.0, le=180.0)
    display_name: str
    provider: str
    result_type: GeocodingResultType = GeocodingResultType.UNKNOWN
    confidence: float = Field(..., ge=0.0, le=1.0)
    is_exact: bool = False
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    provenance: GeocodingProvenance = GeocodingProvenance.LIVE_PROVIDER
    raw_metadata: dict[str, Any] = Field(default_factory=dict)

    from pydantic import model_validator

    @model_validator(mode="before")
    @classmethod
    def _remap_lat_lng(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "lat" not in data and "latitude" in data:
                data["lat"] = data["latitude"]
            if "lng" not in data and "longitude" in data:
                data["lng"] = data["longitude"]
        return data

    @property
    def latitude(self) -> float:
        return self.lat

    @property
    def longitude(self) -> float:
        return self.lng


class GeocodingResolutionError(Exception):
    """Raised when geocoding fails or returns low-confidence / ambiguous results."""
    def __init__(self, message: str, query: str, status: str = "unresolved_location"):
        super().__init__(message)
        self.message = message
        self.query = query
        self.status = status


def parse_coordinate_query(query: str) -> Optional[GeocodingResult]:
    """
    Parses direct latitude and longitude coordinates if provided in numeric format.
    Example: '28.6270, 77.3650' or '28.6270,77.3650'.
    """
    coord_pattern = r"^[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)$"
    cleaned = query.strip()
    if re.match(coord_pattern, cleaned):
        try:
            parts = cleaned.split(",")
            lat = float(parts[0].strip())
            lng = float(parts[1].strip())
            return GeocodingResult(
                query=query,
                lat=lat,
                lng=lng,
                display_name=f"Coordinates ({lat:.4f}, {lng:.4f})",
                provider="coordinate",
                result_type=GeocodingResultType.COORDINATE,
                confidence=1.0,
                is_exact=True,
                timestamp=datetime.now(timezone.utc),
                provenance=GeocodingProvenance.USER_COORDINATE,
                raw_metadata={"parsed": True},
            )
        except (ValueError, IndexError):
            return None
    return None


class GeocodingProvider(ABC):
    """Abstract interface for confidence-aware geocoding providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the geocoding provider."""
        pass

    @abstractmethod
    async def geocode(self, query: str) -> Optional[GeocodingResult]:
        """
        Resolves a location query string into a GeocodingResult.
        Returns None if the provider cannot find the location.
        """
        pass
