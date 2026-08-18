import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from unittest.mock import MagicMock
from ml.intelligence.temporal_engine import analyze_temporal

class MockChangeRecord:
    def __init__(self, id, location_name, area_sq_m, detected_at, mask_geojson=None):
        self.id = id
        self.location_name = location_name
        self.area_sq_m = area_sq_m
        self.detected_at = detected_at
        self.mask_geojson = mask_geojson
        # Add attributes required by temporal_engine.py query and logic
        self.after_image_date = detected_at
        self.before_image_date = detected_at

def test_analyze_temporal_new():
    session = MagicMock()
    # Return a current record
    current = MockChangeRecord("id1", "loc1", 100, None)
    session.execute.return_value.scalar_one_or_none.return_value = current
    
    # Return only the current record for the query
    session.execute.return_value.scalars.return_value.all.return_value = []
    
    res = analyze_temporal("id1", 100, None, session)
    assert res['temporal_status'] == 'new'
    assert res['observation_count'] == 1

def test_analyze_temporal_expanding():
    session = MagicMock()
    import datetime
    current = MockChangeRecord("id1", "loc1", 200, datetime.datetime.now(), '{"features":[{"geometry":{"type":"Polygon","coordinates":[[[0,0],[0,10],[10,10],[10,0],[0,0]]]}}]}')
    historical = MockChangeRecord("id2", "loc1", 100, datetime.datetime.now() - datetime.timedelta(days=1), '{"features":[{"geometry":{"type":"Polygon","coordinates":[[[0,0],[0,5],[5,5],[5,0],[0,0]]]}}]}')
    
    session.execute.return_value.scalar_one_or_none.return_value = current
    session.execute.return_value.scalars.return_value.all.return_value = [historical]
    
    res = analyze_temporal("id1", 200, None, session)
    assert res['temporal_status'] == 'expanding'
    assert res['observation_count'] == 2
    assert res['growth_rate_pct'] == 100.0

