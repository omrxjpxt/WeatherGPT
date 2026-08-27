from typing import List, Optional
from app.models.base import WeatherBaseModel
from app.models.enums import RiskLevel, ConfidenceLevel

class Confidence(WeatherBaseModel):
    level: ConfidenceLevel
    percentage: int
    explanation: str

class RiskFactor(WeatherBaseModel):
    name: str
    description: str
    score: int
    level: RiskLevel
    weight: float

class RiskAssessment(WeatherBaseModel):
    overall_score: int
    level: RiskLevel
    confidence: Confidence
    factors: List[RiskFactor]
    summary: str
