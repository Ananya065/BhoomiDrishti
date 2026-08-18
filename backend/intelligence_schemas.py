"""
Pydantic schemas for Part 2 intelligence API responses.
These extend — but do not modify — the existing schemas.py.
"""
from pydantic import BaseModel
from typing import Optional, List


class ClassificationOut(BaseModel):
    activity_type: str
    confidence: float
    method: str
    status: str
    evidence: Optional[str] = None


class GeospatialOut(BaseModel):
    sensitive_zone: bool
    zone_type: Optional[str] = None
    overlap_area_sq_m: float = 0.0
    overlap_percentage: float = 0.0
    status: str
    evidence: Optional[str] = None


class SeverityOut(BaseModel):
    level: str
    score: float
    reason: Optional[str] = None


class TemporalOut(BaseModel):
    status: str
    first_detected: Optional[str] = None
    last_detected: Optional[str] = None
    observation_count: int = 1
    area_progression: Optional[str] = None
    growth_rate_pct: Optional[float] = None


class IntelligenceOut(BaseModel):
    change_id: str
    classification: ClassificationOut
    geospatial: GeospatialOut
    severity: SeverityOut
    temporal: TemporalOut
    analyzed_at: Optional[str] = None


class IntelligenceStatsOut(BaseModel):
    total_analyzed: int = 0
    by_activity: dict = {}
    by_severity: dict = {}
    sensitive_zone_count: int = 0
    avg_severity_score: float = 0.0


class CopilotMessage(BaseModel):
    message: str
    case_id: Optional[str] = None  # None = global mode, set = case mode


class CopilotResponse(BaseModel):
    reply: str
    tool_calls: List[dict] = []
    sources: List[str] = []
    error: Optional[str] = None
