"""
Database setup for BhoomiDrishti.

Uses SQLite for the hackathon build (zero setup). Swapping to Postgres
later only requires changing DATABASE_URL below — the rest of the app
is unaffected because we go through SQLAlchemy's ORM layer.
"""
from sqlalchemy import create_engine, Column, String, Float, DateTime, Boolean, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
import uuid

DATABASE_URL = "sqlite:///./bhoomidrishti.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def gen_id() -> str:
    return uuid.uuid4().hex[:12]


class ChangeRecord(Base):
    """
    One detected change region between a before/after image pair.
    This is the row the frontend map, priority feed, and case file are
    built from. Fields below cover both the detection-model output and
    the govt-portal case-management fields (survey no., officer, timeline).
    """
    __tablename__ = "change_records"

    id = Column(String, primary_key=True, default=gen_id)
    case_number = Column(String, unique=True, nullable=True)   # e.g. "PD2026-0847"

    location_name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    change_type = Column(String, nullable=False)      # building | road | vehicle | aircraft
    confidence = Column(Float, nullable=False)         # 0-1, model confidence
    area_sq_m = Column(Float, nullable=False)          # severity / size scoring
    severity_score = Column(Float, nullable=False)     # 0-100 combined ranking score
    priority = Column(String, default="medium")         # critical | high | medium

    sensitivity_flag = Column(Boolean, default=False)  # True if inside a sensitive zone
    sensitivity_zone_type = Column(String, nullable=True)   # forest | protected_area | water_body | none
    sensitivity_zone_name = Column(String, nullable=True)
    sensitivity_note = Column(String, nullable=True)   # e.g. data-quality caveat

    before_image_date = Column(DateTime, nullable=False)
    after_image_date = Column(DateTime, nullable=False)
    detected_at = Column(DateTime, default=datetime.datetime.utcnow)

    before_image_url = Column(String, nullable=True)
    after_image_url = Column(String, nullable=True)
    mask_geojson = Column(String, nullable=True)  # polygon of the change region, as GeoJSON string

    district = Column(String, nullable=True)
    taluka = Column(String, nullable=True)
    village = Column(String, nullable=True)
    survey_number = Column(String, nullable=True)

    status = Column(String, default="needs_review")  # needs_review | reviewed | dismissed

    # --- case-management fields (govt portal) ---
    assigned_officer = Column(String, nullable=True)
    land_class_type = Column(String, nullable=True)     # e.g. "Agricultural (Reserved Govt.)"
    deeded_owner = Column(String, nullable=True)
    registered_area_hectares = Column(Float, nullable=True)
    timeline_json = Column(String, nullable=True)  # JSON list of {stage, date, description, done}
    notes_json = Column(String, nullable=True)      # JSON list of {author, date, text}


def init_db():
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
