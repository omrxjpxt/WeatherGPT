import pytest
from datetime import datetime, timezone, timedelta
from app.services.trip_service import TripService
from app.decision_engine.normalized_models import NormalizedAlert
from app.models.enums import AlertSourceClass, AlertSeverity
from app.core.config import settings

def test_authoritative_source_follows_application_policy():
    # Setup
    now = datetime.now(timezone.utc)
    alert = NormalizedAlert(
        id="a1", source_name="IMD", source_class=AlertSourceClass.authoritative,
        severity=AlertSeverity.emergency, affected_areas_polygon=[],
        issued_at=now, expires_at=None, is_override_eligible=False
    )
    
    # We can test the TripService policy evaluator directly
    service = TripService(weather_provider=None, routing_provider=None, alert_provider=None)
    evaluated = service._evaluate_alert_policy([alert])
    
    assert evaluated[0].is_override_eligible is True

def test_secondary_provider_cannot_self_declare_override_eligibility():
    now = datetime.now(timezone.utc)
    # A rogue secondary provider tries to claim it is eligible for override
    alert = NormalizedAlert(
        id="a1", source_name="Some API", source_class=AlertSourceClass.secondary,
        severity=AlertSeverity.emergency, affected_areas_polygon=[],
        issued_at=now, expires_at=None, is_override_eligible=True # Maliciously set to true
    )
    
    service = TripService(weather_provider=None, routing_provider=None, alert_provider=None)
    evaluated = service._evaluate_alert_policy([alert])
    
    # The policy should reject it and set it back to False
    assert evaluated[0].is_override_eligible is False

def test_demo_override_works_in_demo_mode(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    now = datetime.now(timezone.utc)
    alert = NormalizedAlert(
        id="a1", source_name="Mock", source_class=AlertSourceClass.demo,
        severity=AlertSeverity.emergency, affected_areas_polygon=[],
        issued_at=now, expires_at=None, is_override_eligible=False
    )
    
    service = TripService(weather_provider=None, routing_provider=None, alert_provider=None)
    evaluated = service._evaluate_alert_policy([alert])
    
    # Should be True because demo_mode is True
    assert evaluated[0].is_override_eligible is True

def test_demo_override_blocked_in_production_mode(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", False) # Production mode
    now = datetime.now(timezone.utc)
    alert = NormalizedAlert(
        id="a1", source_name="Mock", source_class=AlertSourceClass.demo,
        severity=AlertSeverity.emergency, affected_areas_polygon=[],
        issued_at=now, expires_at=None, is_override_eligible=True # Try to bypass
    )
    
    service = TripService(weather_provider=None, routing_provider=None, alert_provider=None)
    evaluated = service._evaluate_alert_policy([alert])
    
    # Should be False because demo_mode is False
    assert evaluated[0].is_override_eligible is False
