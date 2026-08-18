"""
Pydantic schemas = the API contract between backend, frontend, and
(eventually) the real ML model. Keep this file as the single source of
truth for field names/shapes so nobody has to guess what JSON to send.
"""
from pydantic import BaseModel
from typing import Optional, List
import datetime


class TimelineStage(BaseModel):
    stage: str
    date: str
    description: str
    done: bool


class CaseNote(BaseModel):
    author: str
    date: str
    text: str


class ChangeRecordOut(BaseModel):
    id: str
    case_number: Optional[str] = None
    location_name: str
    latitude: float
    longitude: float

    change_type: str
    confidence: float
    area_sq_m: float
    severity_score: float
    priority: str

    sensitivity_flag: bool
    sensitivity_zone_type: Optional[str] = None
    sensitivity_zone_name: Optional[str] = None
    sensitivity_note: Optional[str] = None

    before_image_date: datetime.datetime
    after_image_date: datetime.datetime
    detected_at: datetime.datetime

    before_image_url: Optional[str] = None
    after_image_url: Optional[str] = None
    mask_geojson: Optional[str] = None

    district: Optional[str] = None
    taluka: Optional[str] = None
    village: Optional[str] = None
    survey_number: Optional[str] = None
    status: str

    assigned_officer: Optional[str] = None
    land_class_type: Optional[str] = None
    deeded_owner: Optional[str] = None
    registered_area_hectares: Optional[float] = None

    class Config:
        from_attributes = True


class CaseDetailOut(ChangeRecordOut):
    """Full case file: everything in ChangeRecordOut plus timeline + notes."""
    timeline: List[TimelineStage] = []
    notes: List[CaseNote] = []


class DetectRequest(BaseModel):
    """
    What the frontend sends to trigger a detection run.
    In the mock backend this just picks a demo scenario; once the real
    model is ready, before_image_url/after_image_url should point to the
    actual uploaded/ingested image pair and this same shape still works.
    """
    location_name: str
    latitude: float
    longitude: float
    before_image_url: Optional[str] = None
    after_image_url: Optional[str] = None
    before_image_date: Optional[datetime.datetime] = None
    after_image_date: Optional[datetime.datetime] = None


class StatusUpdate(BaseModel):
    status: str  # needs_review | reviewed | dismissed


class OfficerAssign(BaseModel):
    assigned_officer: str


class AddNoteRequest(BaseModel):
    author: str
    text: str


class ReportOut(BaseModel):
    """Auto-generated evidence report for a single flagged change (5.6 in blueprint)."""
    change_id: str
    case_number: Optional[str]
    location_name: str
    coordinates: str
    detected_date: str
    change_type: str
    estimated_area_sq_m: float
    confidence_pct: str
    sensitivity_flag: bool
    sensitivity_zone: Optional[str]
    before_image_url: Optional[str]
    after_image_url: Optional[str]
    disclaimer: str


class LoginRequest(BaseModel):
    username: str
    password: str
    role: str = "District Officer"


class LoginResponse(BaseModel):
    token: str
    name: str
    role: str
    district: str
