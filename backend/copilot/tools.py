"""
Copilot tools — structured database queries that the Groq LLM can invoke.

These are the ONLY source of factual data for the copilot.  The LLM must
call these tools rather than fabricating case IDs, areas, or statistics.
Every function returns a plain Python dict that is JSON-serializable.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from database import ChangeRecord
from intelligence_models import IntelligenceRecord
import json
import datetime


# ---------------------------------------------------------------------------
# Tool definitions (JSON schema for Groq function-calling)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_cases",
            "description": "Search change-detection cases with optional filters. Returns a list of matching cases with basic info.",
            "parameters": {
                "type": "object",
                "properties": {
                    "activity_type": {"type": "string", "description": "Filter by activity type: construction, deforestation, mining, encroachment, other, unknown"},
                    "severity_level": {"type": "string", "description": "Filter by severity: CRITICAL, HIGH, MEDIUM, LOW"},
                    "sensitive_zone": {"type": "boolean", "description": "Filter for cases in sensitive zones only"},
                    "status": {"type": "string", "description": "Filter by case status: needs_review, reviewed, dismissed"},
                    "limit": {"type": "integer", "description": "Max number of results to return (default 10)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_case",
            "description": "Get full details of a specific case by its case ID or case number.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_identifier": {"type": "string", "description": "The case ID (e.g. '62ff38d0964a') or case number (e.g. 'PD2026-5C24AD07')"},
                },
                "required": ["case_identifier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_case_intelligence",
            "description": "Get the Part 2 intelligence analysis for a specific case: classification, GIS, severity, and temporal data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_identifier": {"type": "string", "description": "The case ID or case number"},
                },
                "required": ["case_identifier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_high_priority_cases",
            "description": "Get cases with HIGH or CRITICAL severity, sorted by severity score descending.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Max number of results (default 10)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_sensitive_zone_cases",
            "description": "Get cases that overlap with sensitive geographic zones (forests, protected areas, water bodies, etc.).",
            "parameters": {
                "type": "object",
                "properties": {
                    "zone_type": {"type": "string", "description": "Filter by zone type: forest, protected_area, water_body, wetland, agricultural"},
                    "limit": {"type": "integer", "description": "Max number of results (default 10)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_detection_statistics",
            "description": "Get aggregate statistics: total cases, by activity type, by severity, by status, total affected area.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "summarize_case",
            "description": "Get a structured summary of a case combining detection and intelligence data, suitable for report generation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "case_identifier": {"type": "string", "description": "The case ID or case number"},
                },
                "required": ["case_identifier"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def _find_case(db: Session, identifier: str) -> ChangeRecord:
    """Look up a case by ID or case_number."""
    record = db.query(ChangeRecord).filter(ChangeRecord.id == identifier).first()
    if not record:
        record = db.query(ChangeRecord).filter(ChangeRecord.case_number == identifier).first()
    return record


def _case_to_summary(record: ChangeRecord) -> dict:
    """Convert a ChangeRecord to a compact summary dict."""
    return {
        "id": record.id,
        "case_number": record.case_number,
        "location": record.location_name,
        "change_type": record.change_type,
        "confidence": round(record.confidence, 3),
        "area_sq_m": record.area_sq_m,
        "area_hectares": round(record.area_sq_m / 10000, 2),
        "severity_score": record.severity_score,
        "priority": record.priority,
        "sensitivity_flag": record.sensitivity_flag,
        "status": record.status,
        "detected_at": record.detected_at.isoformat() if record.detected_at else None,
    }


def search_cases(db: Session, activity_type: str = None, severity_level: str = None,
                 sensitive_zone: bool = None, status: str = None, limit: int = 10) -> dict:
    """Search cases with optional filters."""
    query = db.query(ChangeRecord)
    
    # Join intelligence for activity/severity filters
    if activity_type or severity_level or sensitive_zone is not None:
        query = query.outerjoin(IntelligenceRecord, ChangeRecord.id == IntelligenceRecord.change_id)
        if activity_type:
            query = query.filter(IntelligenceRecord.activity_type == activity_type)
        if severity_level:
            query = query.filter(IntelligenceRecord.severity_level == severity_level)
        if sensitive_zone is not None:
            query = query.filter(IntelligenceRecord.sensitive_zone == sensitive_zone)
    
    if status:
        query = query.filter(ChangeRecord.status == status)
    
    records = query.order_by(desc(ChangeRecord.severity_score)).limit(limit).all()
    return {
        "count": len(records),
        "cases": [_case_to_summary(r) for r in records],
    }


def get_case(db: Session, case_identifier: str) -> dict:
    """Get full case details."""
    record = _find_case(db, case_identifier)
    if not record:
        return {"error": f"Case '{case_identifier}' not found."}
    return _case_to_summary(record)


def get_case_intelligence(db: Session, case_identifier: str) -> dict:
    """Get intelligence analysis for a case."""
    record = _find_case(db, case_identifier)
    if not record:
        return {"error": f"Case '{case_identifier}' not found."}
    
    intel = db.query(IntelligenceRecord).filter(IntelligenceRecord.change_id == record.id).first()
    if not intel:
        return {
            "case_id": record.id,
            "case_number": record.case_number,
            "intelligence_status": "not_analyzed",
            "message": "No Part 2 intelligence analysis has been performed for this case yet.",
        }
    
    return {
        "case_id": record.id,
        "case_number": record.case_number,
        **intel.to_dict(),
    }


def get_high_priority_cases(db: Session, limit: int = 10) -> dict:
    """Get cases with HIGH or CRITICAL severity."""
    records = (
        db.query(ChangeRecord)
        .join(IntelligenceRecord, ChangeRecord.id == IntelligenceRecord.change_id)
        .filter(IntelligenceRecord.severity_level.in_(["HIGH", "CRITICAL"]))
        .order_by(desc(IntelligenceRecord.severity_score))
        .limit(limit)
        .all()
    )
    return {
        "count": len(records),
        "cases": [_case_to_summary(r) for r in records],
    }


def get_sensitive_zone_cases(db: Session, zone_type: str = None, limit: int = 10) -> dict:
    """Get cases in sensitive zones."""
    query = (
        db.query(ChangeRecord)
        .join(IntelligenceRecord, ChangeRecord.id == IntelligenceRecord.change_id)
        .filter(IntelligenceRecord.sensitive_zone == True)  # noqa: E712
    )
    if zone_type:
        query = query.filter(IntelligenceRecord.sensitive_zone_type == zone_type)
    
    records = query.order_by(desc(IntelligenceRecord.severity_score)).limit(limit).all()
    return {
        "count": len(records),
        "cases": [_case_to_summary(r) for r in records],
    }


def get_detection_statistics(db: Session) -> dict:
    """Get aggregate statistics."""
    total = db.query(ChangeRecord).count()
    total_area = db.query(func.sum(ChangeRecord.area_sq_m)).scalar() or 0
    
    by_status = {}
    for status_val in ["needs_review", "reviewed", "dismissed"]:
        by_status[status_val] = db.query(ChangeRecord).filter(ChangeRecord.status == status_val).count()
    
    # Intelligence-based stats
    by_activity = {}
    by_severity = {}
    sensitive_count = 0
    avg_severity = 0.0
    
    intel_count = db.query(IntelligenceRecord).count()
    if intel_count > 0:
        for row in db.query(IntelligenceRecord.activity_type, func.count()).group_by(IntelligenceRecord.activity_type).all():
            by_activity[row[0]] = row[1]
        for row in db.query(IntelligenceRecord.severity_level, func.count()).group_by(IntelligenceRecord.severity_level).all():
            by_severity[row[0]] = row[1]
        sensitive_count = db.query(IntelligenceRecord).filter(IntelligenceRecord.sensitive_zone == True).count()  # noqa: E712
        avg_severity = db.query(func.avg(IntelligenceRecord.severity_score)).scalar() or 0.0
    
    return {
        "total_cases": total,
        "total_analyzed": intel_count,
        "total_area_sq_m": total_area,
        "total_area_hectares": round(total_area / 10000, 2),
        "by_status": by_status,
        "by_activity": by_activity,
        "by_severity": by_severity,
        "sensitive_zone_count": sensitive_count,
        "avg_severity_score": round(avg_severity, 1),
    }


def summarize_case(db: Session, case_identifier: str) -> dict:
    """Comprehensive case summary for report generation."""
    record = _find_case(db, case_identifier)
    if not record:
        return {"error": f"Case '{case_identifier}' not found."}
    
    intel = db.query(IntelligenceRecord).filter(IntelligenceRecord.change_id == record.id).first()
    
    summary = {
        "case_id": record.id,
        "case_number": record.case_number,
        "location": record.location_name,
        "coordinates": f"{record.latitude:.5f}, {record.longitude:.5f}",
        "detection": {
            "confidence": round(record.confidence, 3),
            "area_sq_m": record.area_sq_m,
            "area_hectares": round(record.area_sq_m / 10000, 2),
            "detected_at": record.detected_at.isoformat() if record.detected_at else None,
        },
        "status": record.status,
        "assigned_officer": record.assigned_officer,
    }
    
    if intel:
        summary["intelligence"] = intel.to_dict()
    else:
        summary["intelligence"] = {"status": "not_analyzed"}
    
    return summary


# ---------------------------------------------------------------------------
# Tool dispatcher — maps tool names to implementations
# ---------------------------------------------------------------------------

TOOL_DISPATCH = {
    "search_cases": search_cases,
    "get_case": get_case,
    "get_case_intelligence": get_case_intelligence,
    "get_high_priority_cases": get_high_priority_cases,
    "get_sensitive_zone_cases": get_sensitive_zone_cases,
    "get_detection_statistics": get_detection_statistics,
    "summarize_case": summarize_case,
}
