import math
from backend.ml.intelligence.severity_config import WEIGHTS, ACTIVITY_SEVERITY, AREA_THRESHOLDS, SEVERITY_LEVELS

def compute_severity(area_sq_m: float, detection_confidence: float, activity_type: str, classification_confidence: float, gis_overlap_pct: float, sensitive_zone: bool) -> dict:
    # area_score: normalize area using log scale against AREA_THRESHOLDS, cap at 100
    if area_sq_m <= 0:
        area_score = 0.0
    else:
        # Scale log_10(area) against log_10(massive) (which is 6)
        area_score = (math.log10(area_sq_m) / 6.0) * 100
        area_score = max(0.0, min(100.0, area_score))
        
    detection_score = max(0.0, min(100.0, detection_confidence * 100))
    activity_score = ACTIVITY_SEVERITY.get(activity_type, 0.2) * 100
    gis_score = 100.0 if sensitive_zone else min(100.0, gis_overlap_pct or 0.0)
    classification_score = max(0.0, min(100.0, classification_confidence * 100))
    
    severity_score = (
        area_score * WEIGHTS['area'] +
        detection_score * WEIGHTS['detection_confidence'] +
        activity_score * WEIGHTS['activity_type'] +
        gis_score * WEIGHTS['gis_overlap'] +
        classification_score * WEIGHTS['classification_confidence']
    )
    
    severity_level = 'LOW'
    for level, threshold in sorted(SEVERITY_LEVELS.items(), key=lambda x: x[1], reverse=True):
        if severity_score >= threshold:
            severity_level = level
            break
            
    ha_area = area_sq_m / 10000.0
    area_desc = "Large-area" if area_sq_m >= AREA_THRESHOLDS['large'] else ("Medium-area" if area_sq_m >= AREA_THRESHOLDS['medium'] else "Small-area")
    zone_desc = " inside a sensitive zone" if sensitive_zone else ""
    
    priority_reason = f"{area_desc} {activity_type} detected ({ha_area:.2f} ha) with high model confidence ({int(detection_score)}%){zone_desc}."
    
    return {
        'severity_score': round(severity_score, 2),
        'severity_level': severity_level,
        'priority_reason': priority_reason
    }
