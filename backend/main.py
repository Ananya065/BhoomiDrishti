"""
BhoomiDrishti backend — FastAPI

Endpoints are built against the API contract in schemas.py. All ML/GIS
logic currently runs through mock_data.py (see that file's docstring for
exactly how to swap in the real model + real sensitivity-zone overlap
logic without touching routes, DB, or frontend).
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
import json
import datetime
import uuid

from database import init_db, get_db, ChangeRecord, SessionLocal
from schemas import (
    ChangeRecordOut, CaseDetailOut, DetectRequest, StatusUpdate, ReportOut,
    OfficerAssign, AddNoteRequest, LoginRequest, LoginResponse,
    TimelineStage, CaseNote,
)
from intelligence_models import IntelligenceRecord
from intelligence_schemas import (
    IntelligenceOut, IntelligenceStatsOut, CopilotMessage, CopilotResponse
)
from copilot.copilot_service import get_copilot_service
import mock_data

app = FastAPI(
    title="BhoomiDrishti API",
    description="Satellite-based human-made change detection with sensitivity-zone flagging (SIH1518)",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before any real deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    init_db()
    db = SessionLocal()
    try:
        mock_data.seed_demo_records(db, ChangeRecord, count=18)
    finally:
        db.close()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "bhoomidrishti-backend"}


# ---------- Auth (mock — no real password check, demo login only) ----------
@app.post("/api/auth/login", response_model=LoginResponse)
def login(req: LoginRequest):
    if not req.username or not req.password:
        raise HTTPException(status_code=400, detail="Username and password required")
    display_name = req.username.split("@")[0].replace(".", " ").title()
    return LoginResponse(
        token=uuid.uuid4().hex,
        name=display_name or "District Officer",
        role=req.role,
        district="Pune",
    )


# ---------- Cases / changes ----------
@app.get("/api/changes", response_model=List[ChangeRecordOut])
def list_changes(
    sensitivity_only: bool = False,
    change_type: Optional[str] = None,
    priority: Optional[str] = None,
    village: Optional[str] = None,
    min_severity: float = 0,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Powers the control-room dashboard and live map. Sorted by severity descending."""
    query = db.query(ChangeRecord)
    if sensitivity_only:
        query = query.filter(ChangeRecord.sensitivity_flag == True)  # noqa: E712
    if change_type:
        query = query.filter(ChangeRecord.change_type == change_type)
    if priority:
        query = query.filter(ChangeRecord.priority == priority)
    if village:
        query = query.filter(ChangeRecord.village == village)
    if status:
        query = query.filter(ChangeRecord.status == status)
    query = query.filter(ChangeRecord.severity_score >= min_severity)
    return query.order_by(desc(ChangeRecord.severity_score)).all()


@app.get("/api/changes/{change_id}", response_model=CaseDetailOut)
def get_change(change_id: str, db: Session = Depends(get_db)):
    """Full case file — includes timeline + officer notes for the Case File screen."""
    record = db.query(ChangeRecord).filter(ChangeRecord.id == change_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Case not found")
    out = CaseDetailOut.model_validate(record)
    out.timeline = [TimelineStage(**t) for t in (json.loads(record.timeline_json) if record.timeline_json else [])]
    out.notes = [CaseNote(**n) for n in (json.loads(record.notes_json) if record.notes_json else [])]
    return out


@app.post("/api/detect-change", response_model=ChangeRecordOut)
def detect_change(req: DetectRequest, db: Session = Depends(get_db)):
    """
    Runs detection on a before/after image pair for a location.
    Backed by real SiameseUNet inference.
    """
    from ml.services.model_service import get_model_service
    import uuid
    import datetime
    import os
    import json

    # Ensure no hardcoded OSCD root paths exist in production. 
    # Must use ENV or fallback to an explicit development path relative to repo or explicitly configured.
    # The frontend doesn't yet upload actual TIFs, so we simulate `uploaded_pair` vs `oscd_sample` via req properties.
    
    inference_mode = req.mode if hasattr(req, "mode") and req.mode else "oscd_sample"
    
    if inference_mode == "oscd_sample":
        # Use explicitly chosen city from request or fallback to Abu Dhabi for demo purposes
        city = (req.location_name or "abudhabi").lower().replace(" ", "")
        
        # Pull from explicitly defined environment variable to ensure portability
        base_dataset_path = os.environ.get("OSCD_DATASET_ROOT", "/data/oscd")
        
        before_path = os.path.join(base_dataset_path, "Onera Satellite Change Detection dataset - Images", city, "imgs_1_rect")
        after_path = os.path.join(base_dataset_path, "Onera Satellite Change Detection dataset - Images", city, "imgs_2_rect")
        
        if not os.path.exists(before_path):
            raise HTTPException(status_code=400, detail=f"OSCD sample not found for city: {city} at {before_path}")
    else:
        # For actual production: 
        if not req.before_image_url or not req.after_image_url:
            raise HTTPException(status_code=400, detail="Missing before_image_url and after_image_url for uploaded_pair mode.")
        before_path = req.before_image_url
        after_path = req.after_image_url

    model_service = get_model_service()
    try:
        prediction = model_service.predict(before_path, after_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {str(e)}")
        
    area_sq_m = prediction["detection"]["area_sq_m"]
    confidence = prediction["detection"]["confidence"]
    geojson = prediction["geojson"]
    
    # Deterministic Unique ID instead of random.randint
    unique_id = uuid.uuid4().hex[:8].upper()
    now = datetime.datetime.utcnow()
    
    record = ChangeRecord(
        case_number=f"PD2026-{unique_id}",
        location_name=req.location_name or (city if inference_mode == "oscd_sample" else "Unknown"),
        latitude=req.latitude,
        longitude=req.longitude,
        change_type="Pending",
        confidence=confidence,
        area_sq_m=area_sq_m,
        severity_score=0.0, # pending
        priority="pending",
        sensitivity_flag=False,
        sensitivity_zone_type=None,
        sensitivity_zone_name=None,
        sensitivity_note="Classification pending PART 2",
        before_image_date=req.before_image_date or now,
        after_image_date=req.after_image_date or now,
        before_image_url=req.before_image_url or "Real Image",
        after_image_url=req.after_image_url or "Real Image",
        mask_geojson=json.dumps(geojson) if geojson else None,
        survey_number=None,
        status="needs_review",
        assigned_officer="Unassigned",
        land_class_type="Pending",
        deeded_owner="Pending",
        registered_area_hectares=0.0,
        timeline_json="[]",
        notes_json="[]"
    )
    
    db.add(record)
    db.flush() # flush to get record.id for intelligence pipeline
    
    # Run intelligence pipeline
    from ml.services.intelligence_service import run_intelligence_pipeline
    try:
        run_intelligence_pipeline(
            db=db,
            change_record=record,
            before_path=before_path,
            after_path=after_path,
            components=prediction.get("regions", []),
            geojson_data=geojson
        )
    except Exception as e:
        print(f"Intelligence pipeline failed: {e}")
        # We don't want a failing intelligence module to kill the core detection
    
    db.commit()
    db.refresh(record)
    return record


# ---------- Intelligence & Copilot ----------
@app.get("/api/cases/{change_id}/intelligence", response_model=IntelligenceOut)
def get_intelligence(change_id: str, db: Session = Depends(get_db)):
    intel = db.query(IntelligenceRecord).filter(IntelligenceRecord.change_id == change_id).first()
    if not intel:
        raise HTTPException(status_code=404, detail="Intelligence not found or not yet processed for this case.")
    return intel.to_dict()

@app.get("/api/stats/intelligence", response_model=IntelligenceStatsOut)
def get_intelligence_stats(db: Session = Depends(get_db)):
    from copilot.tools import get_detection_statistics
    stats = get_detection_statistics(db)
    return IntelligenceStatsOut(
        total_analyzed=stats.get("total_analyzed", 0),
        by_activity=stats.get("by_activity", {}),
        by_severity=stats.get("by_severity", {}),
        sensitive_zone_count=stats.get("sensitive_zone_count", 0),
        avg_severity_score=stats.get("avg_severity_score", 0.0)
    )

@app.post("/api/copilot/chat", response_model=CopilotResponse)
def copilot_chat(msg: CopilotMessage, db: Session = Depends(get_db)):
    service = get_copilot_service()
    res = service.chat(msg.message, msg.case_id, db)
    return CopilotResponse(**res)
@app.patch("/api/changes/{change_id}/status", response_model=ChangeRecordOut)
def update_status(change_id: str, body: StatusUpdate, db: Session = Depends(get_db)):
    """Human reviewer marks a flagged change as reviewed/dismissed (section 10: human stays in the loop)."""
    record = db.query(ChangeRecord).filter(ChangeRecord.id == change_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Case not found")
    if body.status not in ("needs_review", "reviewed", "dismissed"):
        raise HTTPException(status_code=400, detail="Invalid status value")
    record.status = body.status
    db.commit()
    db.refresh(record)
    return record


@app.patch("/api/changes/{change_id}/assign", response_model=ChangeRecordOut)
def assign_officer(change_id: str, body: OfficerAssign, db: Session = Depends(get_db)):
    record = db.query(ChangeRecord).filter(ChangeRecord.id == change_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Case not found")
    record.assigned_officer = body.assigned_officer
    db.commit()
    db.refresh(record)
    return record


@app.post("/api/changes/{change_id}/notes", response_model=CaseDetailOut)
def add_note(change_id: str, body: AddNoteRequest, db: Session = Depends(get_db)):
    """Adds an officer field note to a case file."""
    record = db.query(ChangeRecord).filter(ChangeRecord.id == change_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Case not found")
    notes = json.loads(record.notes_json) if record.notes_json else []
    notes.append({
        "author": body.author,
        "date": datetime.datetime.utcnow().strftime("%b %d, %Y %I:%M %p"),
        "text": body.text,
    })
    record.notes_json = json.dumps(notes)
    db.commit()
    db.refresh(record)
    out = CaseDetailOut.model_validate(record)
    out.timeline = [TimelineStage(**t) for t in (json.loads(record.timeline_json) if record.timeline_json else [])]
    out.notes = [CaseNote(**n) for n in notes]
    return out


@app.get("/api/changes/{change_id}/report", response_model=ReportOut)
def generate_report(change_id: str, db: Session = Depends(get_db)):
    """Auto-generated evidence report (blueprint 5.6)."""
    r = db.query(ChangeRecord).filter(ChangeRecord.id == change_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Case not found")

    return ReportOut(
        change_id=r.id,
        case_number=r.case_number,
        location_name=r.location_name,
        coordinates=f"{r.latitude:.5f}, {r.longitude:.5f}",
        detected_date=r.detected_at.strftime("%d %b %Y"),
        change_type=r.change_type,
        estimated_area_sq_m=r.area_sq_m,
        confidence_pct=f"{r.confidence * 100:.0f}%",
        sensitivity_flag=r.sensitivity_flag,
        sensitivity_zone=r.sensitivity_zone_name,
        before_image_url=r.before_image_url,
        after_image_url=r.after_image_url,
        disclaimer=(
            "This report flags a geographic overlap with a mapped sensitive-zone "
            "boundary and/or a detected structural change. It is not a legal "
            "determination of ownership, permit status, or violation. All flagged "
            "changes require human review against official land records before "
            "any enforcement action."
        ),
    )


# ---------- Dashboard / analytics ----------
@app.get("/api/stats/summary")
def summary_stats(db: Session = Depends(get_db)):
    """Control-room header stats: total alerts, needs verification, field verified, critical."""
    total = db.query(ChangeRecord).count()
    needs_review = db.query(ChangeRecord).filter(ChangeRecord.status == "needs_review").count()
    field_verified = db.query(ChangeRecord).filter(ChangeRecord.status == "reviewed").count()
    critical = db.query(ChangeRecord).filter(ChangeRecord.priority == "critical").count()
    sensitive = db.query(ChangeRecord).filter(ChangeRecord.sensitivity_flag == True).count()  # noqa: E712
    return {
        "total_changes": total,
        "needs_review": needs_review,
        "field_verified": field_verified,
        "critical_exceptions": critical,
        "sensitive_zone_flags": sensitive,
    }


@app.get("/api/analytics/summary")
def analytics_summary(db: Session = Depends(get_db)):
    """Powers the Analytics & Reports screen: resolution rate, category breakdown, etc."""
    total = db.query(ChangeRecord).count()
    resolved = db.query(ChangeRecord).filter(ChangeRecord.status == "reviewed").count()
    pending = db.query(ChangeRecord).filter(ChangeRecord.status == "needs_review").count()
    resolution_rate = round((resolved / total) * 100) if total else 0

    by_village = {}
    for r in db.query(ChangeRecord).all():
        by_village[r.village] = by_village.get(r.village, 0) + 1

    category_breakdown = {}
    for r in db.query(ChangeRecord).all():
        key = r.change_type
        if key not in category_breakdown:
            category_breakdown[key] = {"total": 0, "resolved": 0}
        category_breakdown[key]["total"] += 1
        if r.status == "reviewed":
            category_breakdown[key]["resolved"] += 1

    return {
        "total_cases": total,
        "resolution_rate_pct": resolution_rate,
        "avg_resolution_days": 14,  # static demo figure until real timestamps are tracked
        "pending_verification": pending,
        "by_village_hotspot": by_village,
        "category_breakdown": category_breakdown,
    }


@app.get("/api/timeline")
def timeline_feed(location_name: Optional[str] = None, db: Session = Depends(get_db)):
    """Powers Multi-Temporal Timeline Mode (5.3) — changes ordered by detection date."""
    query = db.query(ChangeRecord)
    if location_name:
        query = query.filter(ChangeRecord.location_name == location_name)
    records = query.order_by(ChangeRecord.after_image_date).all()
    return [
        {
            "id": r.id,
            "case_number": r.case_number,
            "location_name": r.location_name,
            "date": r.after_image_date.isoformat(),
            "change_type": r.change_type,
            "severity_score": r.severity_score,
            "sensitivity_flag": r.sensitivity_flag,
        }
        for r in records
    ]
