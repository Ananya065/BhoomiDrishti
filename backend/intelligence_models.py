"""
Intelligence record model for Part 2.

Linked 1:1 to the existing ChangeRecord via change_id foreign key.
This preserves full backward compatibility with Part 1 data — no columns
are added to or removed from the change_records table.
"""
from sqlalchemy import Column, String, Float, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import datetime


class IntelligenceRecord(Base):
    """
    Stores Part 2 intelligence for a single ChangeRecord:
    classification, GIS, severity, and temporal analysis results.
    """
    __tablename__ = "intelligence_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    change_id = Column(String, ForeignKey("change_records.id"), unique=True, nullable=False, index=True)

    # --- Classification (Part 2A) ---
    activity_type = Column(String, default="pending")          # construction | deforestation | mining | encroachment | other | unknown | pending
    classification_confidence = Column(Float, default=0.0)     # 0-1, CLIP score
    classification_method = Column(String, default="pending")  # clip_zero_shot | manual | pending
    classification_status = Column(String, default="pending")  # classified | low_confidence | unavailable | error | pending
    classification_evidence = Column(String, nullable=True)    # JSON string of top scores

    # --- GIS / Sensitive-Zone (Part 2B) ---
    sensitive_zone = Column(Boolean, default=False)
    sensitive_zone_type = Column(String, nullable=True)        # forest | protected_area | water_body | wetland | agricultural
    overlap_area_sq_m = Column(Float, default=0.0)
    overlap_percentage = Column(Float, default=0.0)
    gis_status = Column(String, default="pending")             # verified | no_intersection | unavailable | non_georeferenced | error | pending
    gis_evidence = Column(String, nullable=True)               # JSON string of intersecting layers

    # --- Severity (Part 2C) ---
    severity_level = Column(String, default="pending")         # CRITICAL | HIGH | MEDIUM | LOW | pending
    severity_score = Column(Float, default=0.0)                # 0-100
    priority_reason = Column(String, nullable=True)            # Human-readable explanation

    # --- Temporal (Part 2D) ---
    temporal_status = Column(String, default="pending")        # new | persistent | expanding | stable | reduced | insufficient_data | pending
    first_detected = Column(DateTime, nullable=True)
    last_detected = Column(DateTime, nullable=True)
    observation_count = Column(Integer, default=1)
    area_progression = Column(String, nullable=True)           # JSON list of {date, area_sq_m}
    growth_rate_pct = Column(Float, nullable=True)

    # --- Metadata ---
    analyzed_at = Column(DateTime, default=datetime.datetime.utcnow)

    def to_dict(self):
        """Serialize to dict for API responses."""
        return {
            "change_id": self.change_id,
            "classification": {
                "activity_type": self.activity_type,
                "confidence": self.classification_confidence,
                "method": self.classification_method,
                "status": self.classification_status,
                "evidence": self.classification_evidence,
            },
            "geospatial": {
                "sensitive_zone": self.sensitive_zone,
                "zone_type": self.sensitive_zone_type,
                "overlap_area_sq_m": self.overlap_area_sq_m,
                "overlap_percentage": self.overlap_percentage,
                "status": self.gis_status,
                "evidence": self.gis_evidence,
            },
            "severity": {
                "level": self.severity_level,
                "score": self.severity_score,
                "reason": self.priority_reason,
            },
            "temporal": {
                "status": self.temporal_status,
                "first_detected": self.first_detected.isoformat() if self.first_detected else None,
                "last_detected": self.last_detected.isoformat() if self.last_detected else None,
                "observation_count": self.observation_count,
                "area_progression": self.area_progression,
                "growth_rate_pct": self.growth_rate_pct,
            },
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None,
        }
