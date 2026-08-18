"""
Stand-in for the real model + sensitivity-zone overlay pipeline + case
management flow shown in the govt-portal UI design (login, control room,
live map, case file, field verification, analytics).

WHY THIS FILE EXISTS
The ML lead's Siamese/SNUNet model and the Dataset lead's boundary-overlap
logic are not ready yet. This module fakes their *output shape* so the
backend, frontend, and DB can be built and demoed end-to-end today.

HOW TO SWAP IN THE REAL MODEL LATER
Replace `run_mock_detection()` with a call into the real inference code.
As long as the real code returns a dict with the same keys used below,
nothing else in the app (routes, DB, frontend) needs to change.
"""
import random
import json
import datetime
import uuid

CHANGE_TYPES = ["Unauthorized Structure", "Encroachment (Public)", "Land Use Mutation",
                "Encroachment (Forest)", "Excavation/Mining"]
CHANGE_TYPE_SLUGS = {
    "Unauthorized Structure": "building",
    "Encroachment (Public)": "building",
    "Land Use Mutation": "road",
    "Encroachment (Forest)": "building",
    "Excavation/Mining": "vehicle",
}

ZONE_TYPES = [
    ("forest", "Ambegaon Public Forest Reserve"),
    ("protected_area", "Bhima Wildlife Buffer Zone"),
    ("water_body", "Ghod River Floodplain"),
    (None, None),  # no sensitive zone overlap
]

OFFICERS = ["Rajesh Patil", "Sunita Deshmukh", "Anil Kadam", "Meera Joshi"]

LAND_CLASS_TYPES = [
    "Agricultural (Reserved Govt.)",
    "Forest Land (Protected)",
    "Public Common Land (Gairan)",
    "Residential (Private Deeded)",
]

DEMO_LOCATIONS = [
    {"location_name": "Ambegaon, Survey No. 142/3", "latitude": 19.1345, "longitude": 73.8987,
     "district": "Pune", "taluka": "Ambegaon", "village": "Ambegaon", "survey_number": "142/3"},
    {"location_name": "Ambegaon, Survey No. 89/1", "latitude": 19.1290, "longitude": 73.9050,
     "district": "Pune", "taluka": "Ambegaon", "village": "Ambegaon", "survey_number": "89/1"},
    {"location_name": "Ghodegaon, Survey No. 202/A", "latitude": 19.1810, "longitude": 73.7550,
     "district": "Pune", "taluka": "Ambegaon", "village": "Ghodegaon", "survey_number": "202/A"},
    {"location_name": "Manchar, Survey No. 15", "latitude": 19.0000, "longitude": 73.9500,
     "district": "Pune", "taluka": "Ambegaon", "village": "Manchar", "survey_number": "15"},
    {"location_name": "Nirgude, Survey No. 74/2", "latitude": 19.1500, "longitude": 73.8600,
     "district": "Pune", "taluka": "Ambegaon", "village": "Nirgude", "survey_number": "74/2"},
]


def _priority_from_score(score: float) -> str:
    if score >= 70:
        return "critical"
    if score >= 45:
        return "high"
    return "medium"


def _severity(area_sq_m: float, confidence: float, in_sensitive_zone: bool) -> float:
    """Combined priority score (0-100): bigger + more confident + inside sensitive zone ranks higher."""
    size_component = min(area_sq_m / 20, 60)
    confidence_component = confidence * 25
    zone_component = 15 if in_sensitive_zone else 0
    return round(min(size_component + confidence_component + zone_component, 100), 1)


def _build_timeline(detected_date, status, assigned_officer):
    stages = [
        {"stage": "Detected by Satellite System", "date": detected_date.strftime("%b %d, %Y"),
         "description": "Automated analysis flagged a structural change requiring review.", "done": True},
        {"stage": "Officer Assigned", "date": (detected_date + datetime.timedelta(days=1)).strftime("%b %d, %Y"),
         "description": f"Assigned to {assigned_officer} for local assessment.", "done": True},
        {"stage": "On-site Field Verification",
         "date": (detected_date + datetime.timedelta(days=6)).strftime("%b %d, %Y"),
         "description": "Scheduled local physical inspection.", "done": status != "needs_review"},
        {"stage": "Administrative Action", "date": "Pending",
         "description": "Review findings and issue notices if required.", "done": status == "reviewed"},
        {"stage": "Case Resolved", "date": "Pending" if status != "reviewed" else "Closed",
         "description": "Marked verified and logged.", "done": status == "reviewed"},
    ]
    return json.dumps(stages)


def _seed_notes(assigned_officer, detected_date):
    notes = [{
        "author": assigned_officer,
        "date": (detected_date + datetime.timedelta(days=2)).strftime("%b %d, %Y %I:%M %p"),
        "text": "Initiated contact with Gram Panchayat to check if any temporary permits were issued. "
                "Field inspection scheduled.",
    }]
    return json.dumps(notes)


def run_mock_detection(location_name: str, latitude: float, longitude: float,
                        before_date: datetime.datetime = None,
                        after_date: datetime.datetime = None,
                        case_seq: int = None) -> dict:
    """
    Fakes: Siamese CNN diff -> change mask -> classification head -> severity
    scoring -> sensitivity-zone cross-reference -> case assignment.
    Returns a dict matching schemas.ChangeRecordOut fields (minus id, filled
    in by the caller).
    """
    change_type_label = random.choice(CHANGE_TYPES)
    change_type = CHANGE_TYPE_SLUGS[change_type_label]
    confidence = round(random.uniform(0.62, 0.97), 2)
    area_sq_m = round(random.uniform(15, 900), 1)

    zone_type, zone_name = random.choice(ZONE_TYPES)
    in_zone = zone_type is not None
    note = None
    if in_zone:
        note = "Boundary source may be offset by 1-2 km (older forest survey data) — treat as needs-review, not confirmed."

    now = datetime.datetime.utcnow()
    b_date = before_date or (now - datetime.timedelta(days=random.randint(35, 90)))
    a_date = after_date or (now - datetime.timedelta(days=random.randint(1, 30)))

    severity_score = _severity(area_sq_m, confidence, in_zone)
    priority = _priority_from_score(severity_score)
    status = random.choices(["needs_review", "reviewed", "dismissed"], weights=[0.6, 0.3, 0.1])[0]
    assigned_officer = random.choice(OFFICERS)

    seed = uuid.uuid4().hex[:6]
    seq = case_seq if case_seq is not None else random.randint(800, 999)

    return {
        "case_number": f"PD2026-{seq:04d}",
        "location_name": location_name,
        "latitude": latitude,
        "longitude": longitude,
        "change_type": change_type,
        "change_type_label": change_type_label,
        "confidence": confidence,
        "area_sq_m": area_sq_m,
        "severity_score": severity_score,
        "priority": priority,
        "sensitivity_flag": in_zone,
        "sensitivity_zone_type": zone_type,
        "sensitivity_zone_name": zone_name,
        "sensitivity_note": note,
        "before_image_date": b_date,
        "after_image_date": a_date,
        "before_image_url": f"https://placehold.co/512x512/e8edf2/16324f?text=Before+{seed}",
        "after_image_url": f"https://placehold.co/512x512/e8edf2/c0533a?text=After+{seed}",
        "mask_geojson": None,
        "survey_number": None,  # filled from DEMO_LOCATIONS by caller
        "status": status,
        "assigned_officer": assigned_officer,
        "land_class_type": random.choice(LAND_CLASS_TYPES),
        "deeded_owner": "Government of Maharashtra (Revenue Department)",
        "registered_area_hectares": round(random.uniform(0.5, 4.0), 1),
        "timeline_json": _build_timeline(a_date, status, assigned_officer),
        "notes_json": _seed_notes(assigned_officer, a_date),
    }


def seed_demo_records(db_session, ChangeRecord, count: int = 18):
    """Populate the DB with demo case records so the dashboard isn't empty on first run."""
    existing = db_session.query(ChangeRecord).count()
    if existing > 0:
        return
    for i in range(count):
        loc = random.choice(DEMO_LOCATIONS)
        jitter_lat = loc["latitude"] + random.uniform(-0.02, 0.02)
        jitter_lng = loc["longitude"] + random.uniform(-0.02, 0.02)
        data = run_mock_detection(loc["location_name"], jitter_lat, jitter_lng, case_seq=847 + i)
        data.pop("change_type_label", None)
        data["district"] = loc["district"]
        data["taluka"] = loc["taluka"]
        data["village"] = loc["village"]
        data["survey_number"] = loc["survey_number"]
        record = ChangeRecord(**data)
        db_session.add(record)
    db_session.commit()
