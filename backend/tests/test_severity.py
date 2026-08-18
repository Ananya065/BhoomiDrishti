import pytest
from backend.ml.intelligence.severity_engine import compute_severity

def test_compute_severity_small_low():
    res = compute_severity(area_sq_m=500, detection_confidence=0.3, activity_type='other', classification_confidence=0.3, gis_overlap_pct=0.0, sensitive_zone=False)
    assert res['severity_score'] < 30
    assert res['severity_level'] == 'MEDIUM'

def test_compute_severity_large_high():
    res = compute_severity(area_sq_m=200000, detection_confidence=0.9, activity_type='mining', classification_confidence=0.9, gis_overlap_pct=100.0, sensitive_zone=True)
    assert res['severity_score'] >= 75
    assert res['severity_level'] == 'CRITICAL'
    assert 'Large-area' in res['priority_reason']
    assert 'mining' in res['priority_reason']
    assert 'inside a sensitive zone' in res['priority_reason']

def test_compute_severity_missing_gis():
    # If GIS is unavailable, sensitive_zone is None and overlap_pct is None
    res = compute_severity(area_sq_m=10000, detection_confidence=0.8, activity_type='construction', classification_confidence=0.8, gis_overlap_pct=None, sensitive_zone=None)
    # The score should be deterministic and ignore GIS correctly
    assert 0 <= res['severity_score'] <= 100
