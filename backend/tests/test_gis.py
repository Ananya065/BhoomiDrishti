import os
import sys
# Ensure the project root (parent of backend/) is on sys.path so that
# `from backend.ml...` imports resolve when pytest is run from backend/.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import pytest
from backend.ml.gis.gis_service import analyze_region_gis, _LAYER_CACHE


def test_analyze_region_gis_non_georeferenced():
    # Test with OSCD-like geometry (large pixel coords)
    geojson_geom = {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [0.0, 799.0], [785.0, 799.0], [785.0, 0.0], [0.0, 0.0]]]
    }
    result = analyze_region_gis(geojson_geom)
    assert result['gis_status'] == 'non_georeferenced'
    assert result['sensitive_zone'] is None
    assert result['sensitive_zone_type'] is None

def test_analyze_region_gis_unavailable(monkeypatch):
    # Clear cache so any previously-loaded layer doesn't bypass the monkeypatch
    _LAYER_CACHE.clear()
    # Mock get_available_layers to return empty dict
    monkeypatch.setattr('backend.ml.gis.gis_service.get_available_layers', lambda: {})
    geojson_geom = {
        "type": "Polygon",
        "coordinates": [[[73.0, 18.0], [73.0, 18.1], [73.1, 18.1], [73.1, 18.0], [73.0, 18.0]]]
    }
    result = analyze_region_gis(geojson_geom)
    assert result['gis_status'] == 'unavailable'
    assert result['sensitive_zone'] is None
