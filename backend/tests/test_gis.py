import pytest
from backend.ml.gis.gis_service import analyze_region_gis

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
    # Mock get_available_layers to return empty dict
    monkeypatch.setattr('backend.ml.gis.gis_service.get_available_layers', lambda: {})
    geojson_geom = {
        "type": "Polygon",
        "coordinates": [[[73.0, 18.0], [73.0, 18.1], [73.1, 18.1], [73.1, 18.0], [73.0, 18.0]]]
    }
    result = analyze_region_gis(geojson_geom)
    assert result['gis_status'] == 'unavailable'
    assert result['sensitive_zone'] is None
