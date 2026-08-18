"""
Orchestrates the Part 2 Intelligence pipeline (Classification, GIS, Severity, Temporal).
"""
import os
import json
from sqlalchemy.orm import Session
from intelligence_models import IntelligenceRecord
from database import ChangeRecord

from ..classification.classifier import classify_image
from ..gis.gis_service import analyze_region_gis
from ..intelligence.severity_engine import compute_severity
from ..intelligence.temporal_engine import analyze_temporal

def run_intelligence_pipeline(
    db: Session,
    change_record: ChangeRecord,
    before_path: str,
    after_path: str,
    components: list,
    geojson_data: dict
) -> IntelligenceRecord:
    """
    Runs all 4 intelligence engines on a newly detected change and creates an IntelligenceRecord.
    """
    
    # 1. Classification (Part 2A)
    activity_type = "unknown"
    classification_confidence = 0.0
    classification_method = "clip_zero_shot"
    classification_status = "unavailable"
    top_scores = {}
    
    # We classify the primary component (or all and average, but primary is simplest)
    # The classification service needs to extract the crop.
    if components and os.path.exists(after_path):
        try:
            import rasterio
            import numpy as np
            from PIL import Image
            
            primary_comp = max(components, key=lambda x: x.get('pixel_count', 0))
            x, y, w, h = primary_comp['bbox']
            
            # Read bands (OSCD format)
            # Sentinel-2 bands for RGB are B04, B03, B02
            b4_path = os.path.join(after_path, "B04.tif")
            b3_path = os.path.join(after_path, "B03.tif")
            b2_path = os.path.join(after_path, "B02.tif")
            
            if os.path.exists(b4_path) and os.path.exists(b3_path) and os.path.exists(b2_path):
                with rasterio.open(b4_path) as r, rasterio.open(b3_path) as g, rasterio.open(b2_path) as b:
                    window = rasterio.windows.Window(x, y, w, h)
                    r_arr = r.read(1, window=window)
                    g_arr = g.read(1, window=window)
                    b_arr = b.read(1, window=window)
                    
                    rgb = np.stack((r_arr, g_arr, b_arr), axis=-1).astype(np.float32)
                    # Normalize
                    rgb_max = rgb.max() if rgb.max() > 0 else 1
                    rgb = (rgb / rgb_max * 255).astype(np.uint8)
                    
                    pil_img = Image.fromarray(rgb)
                    
                    # Classify!
                    class_res = classify_image(pil_img)
                    activity_type = class_res['activity_type']
                    classification_status = class_res['classification_status']
                    top_scores = class_res.get('top_scores', {})
                    
                    # 'classification_confidence' from classifier is a string ('high', 'medium', 'low')
                    # We store the actual float max probability if available, otherwise estimate
                    if top_scores and activity_type in top_scores:
                        classification_confidence = top_scores[activity_type]
                    else:
                        if class_res['classification_confidence'] == 'high':
                            classification_confidence = 0.8
                        elif class_res['classification_confidence'] == 'medium':
                            classification_confidence = 0.5
                        else:
                            classification_confidence = 0.2
        except Exception as e:
            print(f"Classification failed: {e}")
            classification_status = "error"
            
    # 2. GIS Intelligence (Part 2B)
    try:
        primary_feature = geojson_data['features'][0] if geojson_data['features'] else {}
        geometry = primary_feature.get('geometry', {})
        if geometry:
            gis_res = analyze_region_gis(geometry)
        else:
            raise ValueError("No geometry found in primary feature")
    except Exception as e:
        print(f"GIS failed: {e}")
        gis_res = {
            "sensitive_zone": False,
            "sensitive_zone_type": None,
            "overlap_area_sq_m": 0.0,
            "overlap_percentage": 0.0,
            "gis_status": "error",
            "intersecting_layers": []
        }
        
    # 3. Temporal Intelligence (Part 2D)
    try:
        temp_res = analyze_temporal(change_record.id, change_record.area_sq_m, change_record.detected_at, db)
    except Exception as e:
        print(f"Temporal failed: {e}")
        temp_res = {
            "temporal_status": "error",
            "first_detected": None,
            "last_detected": None,
            "observation_count": 1,
            "area_progression": [],
            "growth_rate_pct": None
        }

    # 4. Severity Engine (Part 2C)
    try:
        sev_res = compute_severity(
            area_sq_m=change_record.area_sq_m,
            detection_confidence=change_record.confidence,
            activity_type=activity_type,
            classification_confidence=classification_confidence,
            gis_overlap_pct=gis_res['overlap_percentage'],
            sensitive_zone=gis_res['sensitive_zone']
        )
    except Exception as e:
        print(f"Severity failed: {e}")
        sev_res = {
            "severity_score": 0.0,
            "severity_level": "unknown",
            "priority_reason": "Failed to compute severity."
        }

    # Create IntelligenceRecord
    intel = IntelligenceRecord(
        change_id=change_record.id,
        activity_type=activity_type,
        classification_confidence=classification_confidence,
        classification_method=classification_method,
        classification_status=classification_status,
        classification_evidence=json.dumps(top_scores) if top_scores else None,
        
        sensitive_zone=gis_res['sensitive_zone'],
        sensitive_zone_type=gis_res['sensitive_zone_type'],
        overlap_area_sq_m=gis_res['overlap_area_sq_m'],
        overlap_percentage=gis_res['overlap_percentage'],
        gis_status=gis_res['gis_status'],
        gis_evidence=json.dumps(gis_res['intersecting_layers']) if gis_res['intersecting_layers'] else None,
        
        severity_level=sev_res['severity_level'],
        severity_score=sev_res['severity_score'],
        priority_reason=sev_res['priority_reason'],
        
        temporal_status=temp_res['temporal_status'],
        first_detected=temp_res['first_detected'],
        last_detected=temp_res['last_detected'],
        observation_count=temp_res['observation_count'],
        area_progression=json.dumps(temp_res['area_progression']) if temp_res['area_progression'] else None,
        growth_rate_pct=temp_res['growth_rate_pct']
    )
    
    # Update ChangeRecord with intelligence highlights (for Dashboard backward compatibility)
    change_record.change_type = activity_type
    change_record.severity_score = sev_res['severity_score']
    if sev_res['severity_level'] in ['CRITICAL', 'HIGH']:
        change_record.priority = 'critical' if sev_res['severity_level'] == 'CRITICAL' else 'high'
    else:
        change_record.priority = 'medium'
        
    change_record.sensitivity_flag = bool(gis_res['sensitive_zone'])
    change_record.sensitivity_zone_name = gis_res['sensitive_zone_type']
    
    # Clear the hardcoded 'Pending PART 2' note
    change_record.sensitivity_note = "Intelligence Layer processed."

    
    try:
        db.add(intel)
        db.commit()
    except Exception as e:
        print(f"Intelligence DB save failed: {e}")
        db.rollback()
        
    return intel
