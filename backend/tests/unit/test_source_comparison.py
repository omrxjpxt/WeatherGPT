import pytest
from datetime import datetime, timezone
from app.decision_engine.source_comparison import compare_weather_sources, AgreementStatus
from app.decision_engine.normalized_models import NormalizedWeatherPoint

def _point(temp=20.0, precip=0.0, wind=10.0, vis=10000.0, cond="Clear"):
    return NormalizedWeatherPoint(
        time=datetime.now(timezone.utc),
        temperature=temp,
        precipitation_mm=precip,
        humidity=50,
        wind_speed=wind,
        wind_gusts=wind,
        visibility=vis,
        condition=cond,
        is_extreme_heat=False,
        is_poor_visibility=False
    )

def test_compare_high_agreement():
    p1 = [_point(temp=20.0, cond="Clear")]
    s1 = [_point(temp=21.0, cond="Sunny")]
    
    res = compare_weather_sources(p1, s1)
    assert res.agreement_status == AgreementStatus.high
    assert not res.comparison_factors

def test_compare_mild_disagreement():
    p1 = [_point(temp=20.0, cond="Clear")]
    # Cloudy vs Clear is not significant, but wind difference is high
    s1 = [_point(temp=20.0, cond="Cloudy", wind=30.0)]
    
    res = compare_weather_sources(p1, s1)
    assert res.agreement_status == AgreementStatus.mild_disagreement

def test_compare_significant_disagreement_temp():
    p1 = [_point(temp=20.0)]
    s1 = [_point(temp=30.0)] # diff > 5C
    
    res = compare_weather_sources(p1, s1)
    assert res.agreement_status == AgreementStatus.significant_disagreement
    assert any("Temperature difference" in f for f in res.comparison_factors)

def test_compare_significant_disagreement_condition():
    p1 = [_point(cond="Clear")]
    s1 = [_point(cond="Heavy Rain")]
    
    res = compare_weather_sources(p1, s1)
    assert res.agreement_status == AgreementStatus.significant_disagreement
    assert any("Significant condition mismatch" in f for f in res.comparison_factors)

def test_missing_secondary():
    p1 = [_point()]
    res = compare_weather_sources(p1, None)
    assert res.agreement_status == AgreementStatus.missing_secondary

def test_missing_primary():
    s1 = [_point()]
    res = compare_weather_sources(None, s1)
    assert res.agreement_status == AgreementStatus.missing_primary
    # Returns secondary as primary timeline
    assert res.primary_timeline == s1

def test_both_unavailable():
    res = compare_weather_sources(None, None)
    assert res.agreement_status == AgreementStatus.both_unavailable
    assert len(res.primary_timeline) == 0
