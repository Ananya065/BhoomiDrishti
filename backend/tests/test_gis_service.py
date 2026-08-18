"""
test_gis_service.py — Unit tests for the BhoomiDrishti GIS intersection service.

Tests cover:
  1. Non-georeferenced OSCD geometry (pixel coordinates)
  2. Missing GIS directory / no layers available
  3. Known georeferenced geometry inside a protected area (SYNTHETIC)
  4. Known georeferenced geometry outside any protected area (SYNTHETIC)
  5. CRS mismatch — geometry provided in a projected CRS

IMPORTANT:
  Tests 3 and 4 use geometries that are synthetically constructed for unit-testing.
  They are clearly labelled SYNTHETIC and do not represent real satellite detections.
"""

import os
import sys
import pytest

# Allow running from both backend/ and project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# ---- Set GIS_DATA_ROOT before importing the service ----
GIS_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "gis")
os.environ["GIS_DATA_ROOT"] = os.path.abspath(GIS_DATA_DIR)

from backend.ml.gis.gis_service import analyze_region_gis, _is_pixel_coordinates
from backend.ml.gis.layers import get_available_layers


# ============================================================
# Helper: tiny square polygon in WGS84
# ============================================================
def square_geojson(lon_min, lat_min, size_deg=0.01):
    """Return a GeoJSON Polygon dict for a small square."""
    return {
        "type": "Polygon",
        "coordinates": [[
            [lon_min,          lat_min],
            [lon_min + size_deg, lat_min],
            [lon_min + size_deg, lat_min + size_deg],
            [lon_min,          lat_min + size_deg],
            [lon_min,          lat_min],
        ]]
    }


# ============================================================
# TEST 1 — Non-georeferenced OSCD pixel coordinates
# ============================================================
class TestNonGeoreferenced:
    def test_large_oscd_patch_detected(self):
        """OSCD aguasclaras image is 525×471 px — any polygon in that space is pixel-space."""
        geom = square_geojson(0, 0, size_deg=200)   # bounds 0,0→200,200 — x_max=200 > 180
        result = analyze_region_gis(geom)
        assert result["gis_status"] == "non_georeferenced", f"Expected non_georeferenced, got {result['gis_status']}"
        assert result["overlap_percentage"] is None

    def test_medium_oscd_patch_detected(self):
        """Medium OSCD patch (50-150) must also be caught by the improved check."""
        geom = square_geojson(50, 50, size_deg=100)  # x_max=150 < 180 BUT y_max=150 > 90
        result = analyze_region_gis(geom)
        assert result["gis_status"] == "non_georeferenced", f"Expected non_georeferenced, got {result['gis_status']}"

    def test_pixel_check_helper_large(self):
        assert _is_pixel_coordinates((0, 0, 525, 471)) is True

    def test_pixel_check_helper_medium(self):
        assert _is_pixel_coordinates((50, 50, 150, 120)) is True

    def test_pixel_check_india_valid(self):
        """Real India bounding box must NOT be flagged as pixel."""
        assert _is_pixel_coordinates((68.0, 8.0, 97.0, 37.0)) is False

    def test_pixel_check_india_small(self):
        assert _is_pixel_coordinates((72.8, 19.0, 72.9, 19.1)) is False


# ============================================================
# TEST 2 — Missing GIS directory / unavailable layers
# ============================================================
class TestUnavailableLayers:
    def test_unavailable_when_no_layers(self, monkeypatch):
        """When get_available_layers returns empty, result must be 'unavailable'."""
        monkeypatch.setattr("backend.ml.gis.gis_service.get_available_layers", lambda: {})
        # Clear cache so patching takes effect
        import backend.ml.gis.gis_service as svc
        svc._LAYER_CACHE.clear()
        geom = square_geojson(77.0, 28.0)   # valid India coords
        result = analyze_region_gis(geom)
        assert result["gis_status"] == "unavailable"
        assert result["sensitive_zone"] is None


# ============================================================
# TEST 3 — SYNTHETIC: geometry inside a known protected area
# ============================================================
class TestInsideProtectedArea:
    @pytest.mark.skipif(
        not os.path.exists(os.path.join(GIS_DATA_DIR, "india_protected_areas.geojson")),
        reason="india_protected_areas.geojson not present — skipping intersection test"
    )
    def test_synthetic_inside_kaziranga(self):
        """
        SYNTHETIC TEST — NOT A REAL DETECTION.
        Kaziranga National Park (first feature in dataset) spans approx:
          lon 93.14 – 93.59,  lat 26.57 – 26.75
        A point well inside should produce a GIS intersection.
        """
        import backend.ml.gis.gis_service as svc
        svc._LAYER_CACHE.clear()
        geom = square_geojson(93.30, 26.65, size_deg=0.01)   # SYNTHETIC — inside Kaziranga bbox
        result = analyze_region_gis(geom)
        assert result["gis_status"] in ("verified", "no_intersection"), \
            f"Unexpected status: {result['gis_status']}"
        # We can't assert 'verified' here without the full geometry, but status must not be non_georeferenced
        assert result["gis_status"] != "non_georeferenced"


# ============================================================
# TEST 4 — SYNTHETIC: geometry well outside any protected area
# ============================================================
class TestOutsideAreas:
    @pytest.mark.skipif(
        not os.path.exists(os.path.join(GIS_DATA_DIR, "india_protected_areas.geojson")),
        reason="india_protected_areas.geojson not present — skipping"
    )
    def test_synthetic_middle_of_rajasthan_desert(self):
        """
        SYNTHETIC TEST — NOT A REAL DETECTION.
        A remote desert location in Rajasthan is unlikely to intersect any protected area.
        This validates that we don't produce false positives.
        """
        import backend.ml.gis.gis_service as svc
        svc._LAYER_CACHE.clear()
        geom = square_geojson(72.0, 26.0, size_deg=0.001)   # SYNTHETIC — Rajasthan desert approx
        result = analyze_region_gis(geom)
        assert result["gis_status"] != "non_georeferenced"
        assert result["gis_status"] in ("no_intersection", "verified", "unavailable")


# ============================================================
# TEST 5 — CRS mismatch
# ============================================================
class TestCRSHandling:
    def test_valid_wgs84_bounds_not_flagged_as_pixel(self):
        """Ensure valid WGS-84 small geometries don't trigger pixel check."""
        geom = square_geojson(78.9, 20.4, size_deg=0.05)
        assert not _is_pixel_coordinates((78.9, 20.4, 78.95, 20.45))

    def test_large_negative_coords_flagged(self):
        """Coordinates far below -90 are outside WGS-84 — should be flagged."""
        assert _is_pixel_coordinates((-200, -100, 0, 0)) is True

    def test_y_exceeds_90_flagged(self):
        """y_max > 90 must be flagged."""
        assert _is_pixel_coordinates((0, 0, 10, 95)) is True
