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
            "description": (
                "Search change-detection cases with optional filters. Returns a list of matching "
                "cases with basic info drawn from the live ChangeRecord database. "
                "Use this to answer questions about how many cases match a condition."
            ),
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
            "description": (
                "Get full details of a specific case by its case ID or case number. "
                "Returns all ChangeRecord fields: location, coordinates, change type, confidence, "
                "area, severity score, priority, sensitivity flag, district, taluka, village, "
                "survey number, status, assigned officer, land class type, deeded owner, "
                "image dates. Use this for any question about a specific case."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "case_identifier": {"type": "string", "description": "The case ID (e.g. '62ff38d0964a') or case number (e.g. 'PD2026-0857')"},
                },
                "required": ["case_identifier"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_case_intelligence",
            "description": (
                "Get intelligence and case data for a specific case. "
                "Always returns the base ChangeRecord fields (priority, severity_score, change_type, "
                "area, confidence, location, survey number, sensitivity, etc.) even when no "
                "Part 2 intelligence analysis exists. If Part 2 analysis is available, it also "
                "returns detailed classification, GIS, and temporal data. "
                "Use this to answer questions about severity, priority, and why a case was flagged."
            ),
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
            "description": (
                "Get cases with HIGH or CRITICAL priority/severity, sorted by severity score descending. "
                "Returns results from the ChangeRecord priority field even when no Part 2 analysis exists."
            ),
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
            "description": (
                "Get cases that overlap with sensitive geographic zones (forests, protected areas, "
                "water bodies, etc.). Returns results from ChangeRecord.sensitivity_flag even "
                "when no Part 2 analysis exists."
            ),
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
            "description": "Get aggregate statistics: total cases, by status, by priority, total affected area. Also includes Part 2 intelligence stats if available.",
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
            "description": "Get a structured summary of a case combining all available detection and intelligence data, suitable for report generation.",
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


def _to_iso(val) -> str | None:
    """Safely convert a datetime or string to ISO string for JSON serialisation."""
    if val is None:
        return None
    if isinstance(val, str):
        return val
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


def _case_to_full(record: ChangeRecord) -> dict:
    """Convert a ChangeRecord to a full detail dict with all available fields."""
    return {
        "id": record.id,
        "case_number": record.case_number,
        "location_name": record.location_name,
        "district": getattr(record, "district", None),
        "taluka": getattr(record, "taluka", None),
        "village": getattr(record, "village", None),
        "survey_number": getattr(record, "survey_number", None),
        "latitude": record.latitude,
        "longitude": record.longitude,
        "change_type": record.change_type,
        "confidence": round(record.confidence, 3),
        "confidence_pct": f"{round(record.confidence * 100, 1)}%",
        "area_sq_m": record.area_sq_m,
        "area_hectares": round(record.area_sq_m / 10000, 4),
        "severity_score": record.severity_score,
        "priority": record.priority,
        "status": record.status,
        "assigned_officer": record.assigned_officer,
        "land_class_type": getattr(record, "land_class_type", None),
        "deeded_owner": getattr(record, "deeded_owner", None),
        "sensitivity_flag": record.sensitivity_flag,
        "sensitivity_zone_type": getattr(record, "sensitivity_zone_type", None),
        "sensitivity_zone_name": getattr(record, "sensitivity_zone_name", None),
        "before_image_date": _to_iso(getattr(record, "before_image_date", None)),
        "after_image_date": _to_iso(getattr(record, "after_image_date", None)),
        "detected_at": _to_iso(record.detected_at),
    }


def search_cases(db: Session, activity_type: str = None, severity_level: str = None,
                 sensitive_zone: bool = None, status: str = None, limit: int = 10) -> dict:
    """Search cases with optional filters."""
    query = db.query(ChangeRecord)

    # If intelligence-specific filters are requested, try joining IntelligenceRecord
    if activity_type or severity_level:
        query = query.outerjoin(IntelligenceRecord, ChangeRecord.id == IntelligenceRecord.change_id)
        if activity_type:
            query = query.filter(IntelligenceRecord.activity_type == activity_type)
        if severity_level:
            # Try IntelligenceRecord severity first; fall back to ChangeRecord priority
            query = query.filter(IntelligenceRecord.severity_level == severity_level)

    # sensitivity_flag lives on ChangeRecord directly — no join needed
    if sensitive_zone is not None:
        query = query.filter(ChangeRecord.sensitivity_flag == sensitive_zone)

    if status:
        query = query.filter(ChangeRecord.status == status)

    records = query.order_by(desc(ChangeRecord.severity_score)).limit(limit).all()
    return {
        "count": len(records),
        "cases": [_case_to_summary(r) for r in records],
    }


def get_case(db: Session, case_identifier: str) -> dict:
    """Get full case details from ChangeRecord."""
    record = _find_case(db, case_identifier)
    if not record:
        return {"error": f"Case '{case_identifier}' not found."}
    return _case_to_full(record)


def get_case_intelligence(db: Session, case_identifier: str) -> dict:
    """
    Get intelligence and base case data for a case.

    Always returns the full ChangeRecord fields so the LLM can answer questions
    about severity, priority, change type, etc. even without Part 2 analysis.
    If a Part 2 IntelligenceRecord exists, its data is merged in under
    'advanced_intelligence'. If not, 'advanced_intelligence' is clearly marked
    as unavailable — no fabrication.
    """
    record = _find_case(db, case_identifier)
    if not record:
        return {"error": f"Case '{case_identifier}' not found."}

    # Always return full base case data
    result = _case_to_full(record)

    # Attempt to fetch Part 2 intelligence
    intel = db.query(IntelligenceRecord).filter(IntelligenceRecord.change_id == record.id).first()
    if intel:
        result["advanced_intelligence_status"] = "available"
        result["advanced_intelligence"] = intel.to_dict()
    else:
        result["advanced_intelligence_status"] = "not_analyzed"
        result["advanced_intelligence"] = {
            "note": (
                "No Part 2 intelligence analysis has been performed for this case yet. "
                "The satellite change-detection system flagged this case based on pixel-level "
                "change detection. Advanced classification (activity type, GIS overlay, "
                "temporal progression) requires the ML inference pipeline to be run."
            )
        }

    return result


def get_high_priority_cases(db: Session, limit: int = 10) -> dict:
    """
    Get cases with HIGH or CRITICAL priority/severity.
    Uses IntelligenceRecord when available; falls back to ChangeRecord.priority.
    """
    # First try IntelligenceRecord-based query
    intel_records = (
        db.query(ChangeRecord)
        .join(IntelligenceRecord, ChangeRecord.id == IntelligenceRecord.change_id)
        .filter(IntelligenceRecord.severity_level.in_(["HIGH", "CRITICAL"]))
        .order_by(desc(IntelligenceRecord.severity_score))
        .limit(limit)
        .all()
    )

    if intel_records:
        return {
            "count": len(intel_records),
            "source": "part2_intelligence",
            "cases": [_case_to_summary(r) for r in intel_records],
        }

    # Fallback: use ChangeRecord.priority field directly
    fallback_records = (
        db.query(ChangeRecord)
        .filter(ChangeRecord.priority.in_(["critical", "high"]))
        .order_by(desc(ChangeRecord.severity_score))
        .limit(limit)
        .all()
    )
    return {
        "count": len(fallback_records),
        "source": "change_record_priority",
        "note": "Part 2 intelligence not yet run. Results based on initial severity scoring.",
        "cases": [_case_to_summary(r) for r in fallback_records],
    }


def get_sensitive_zone_cases(db: Session, zone_type: str = None, limit: int = 10) -> dict:
    """
    Get cases in sensitive zones.
    Uses IntelligenceRecord when available; falls back to ChangeRecord.sensitivity_flag.
    """
    # First try IntelligenceRecord-based query
    intel_query = (
        db.query(ChangeRecord)
        .join(IntelligenceRecord, ChangeRecord.id == IntelligenceRecord.change_id)
        .filter(IntelligenceRecord.sensitive_zone == True)  # noqa: E712
    )
    if zone_type:
        intel_query = intel_query.filter(IntelligenceRecord.sensitive_zone_type == zone_type)

    intel_records = intel_query.order_by(desc(IntelligenceRecord.severity_score)).limit(limit).all()

    if intel_records:
        return {
            "count": len(intel_records),
            "source": "part2_intelligence",
            "cases": [_case_to_summary(r) for r in intel_records],
        }

    # Fallback: use ChangeRecord.sensitivity_flag
    fallback_query = db.query(ChangeRecord).filter(ChangeRecord.sensitivity_flag == True)  # noqa: E712
    if zone_type:
        fallback_query = fallback_query.filter(
            ChangeRecord.sensitivity_zone_type == zone_type
        )

    fallback_records = fallback_query.order_by(desc(ChangeRecord.severity_score)).limit(limit).all()
    return {
        "count": len(fallback_records),
        "source": "change_record_sensitivity_flag",
        "note": "Part 2 intelligence not yet run. Results based on initial GIS sensitivity flag.",
        "cases": [_case_to_summary(r) for r in fallback_records],
    }


def get_detection_statistics(db: Session) -> dict:
    """Get aggregate statistics."""
    total = db.query(ChangeRecord).count()
    total_area = db.query(func.sum(ChangeRecord.area_sq_m)).scalar() or 0

    by_status = {}
    for status_val in ["needs_review", "reviewed", "dismissed"]:
        by_status[status_val] = db.query(ChangeRecord).filter(ChangeRecord.status == status_val).count()

    # Priority breakdown from ChangeRecord (always available)
    by_priority = {}
    for p in ["critical", "high", "medium", "low"]:
        by_priority[p] = db.query(ChangeRecord).filter(ChangeRecord.priority == p).count()

    # Intelligence-based stats (only if Part 2 has been run)
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
    else:
        # Fallback: sensitivity count from ChangeRecord
        sensitive_count = db.query(ChangeRecord).filter(ChangeRecord.sensitivity_flag == True).count()  # noqa: E712

    return {
        "total_cases": total,
        "total_analyzed_with_intelligence": intel_count,
        "total_area_sq_m": total_area,
        "total_area_hectares": round(total_area / 10000, 2),
        "by_status": by_status,
        "by_priority": by_priority,
        "by_activity_type": by_activity,
        "by_severity_level": by_severity,
        "sensitive_zone_count": sensitive_count,
        "avg_severity_score": round(avg_severity, 1),
    }


def summarize_case(db: Session, case_identifier: str) -> dict:
    """Comprehensive case summary for report generation."""
    record = _find_case(db, case_identifier)
    if not record:
        return {"error": f"Case '{case_identifier}' not found."}

    intel = db.query(IntelligenceRecord).filter(IntelligenceRecord.change_id == record.id).first()

    summary = _case_to_full(record)
    summary["intelligence_analysis"] = intel.to_dict() if intel else {
        "status": "not_analyzed",
        "note": "No Part 2 intelligence analysis available. The above fields are from the initial detection pipeline."
    }

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
