"""
gis_service.py — Spatial intersection between detected regions and GIS layers.

Key behaviours:
  - Returns gis_status='non_georeferenced' when the input geometry uses pixel
    coordinates (outside the valid lat/lon range of [-180,180] x [-90,90]).
  - Returns gis_status='unavailable' when no GIS layer files are found on disk.
  - Caches loaded GIS layers in memory to avoid re-parsing the large water file
    on every request.
  - Repairs invalid geometries in-memory (buffer(0)) without touching source files.
  - Always performs CRS-aware intersection — never compares coordinates from
    different CRS directly.
"""

import logging
from functools import lru_cache
from typing import Dict, Any, Optional

import geopandas as gpd
from shapely.geometry import shape, mapping
from shapely.validation import make_valid

from backend.ml.gis.layers import get_available_layers

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Layer cache — loaded once per process lifetime.
# The 442 MB water file takes ~5–15 s to load; caching avoids repeating that.
# ---------------------------------------------------------------------------
_LAYER_CACHE: Dict[str, gpd.GeoDataFrame] = {}


def _load_layer(name: str, filepath: str) -> Optional[gpd.GeoDataFrame]:
    """Load and cache a GIS layer.  Repairs invalid geometries in-memory."""
    if name in _LAYER_CACHE:
        return _LAYER_CACHE[name]
    try:
        logger.info(f"Loading GIS layer '{name}' from {filepath} ...")
        gdf = gpd.read_file(filepath)

        # Ensure CRS is set.  If the file has no CRS metadata, assume EPSG:4326
        # (standard for GeoJSON per RFC 7946) and log a warning.
        if gdf.crs is None:
            logger.warning(f"Layer '{name}' has no CRS — assuming EPSG:4326 (GeoJSON default).")
            gdf = gdf.set_crs("EPSG:4326")

        # Repair invalid geometries in-memory without altering source files.
        invalid_mask = ~gdf.geometry.is_valid
        if invalid_mask.any():
            n_invalid = invalid_mask.sum()
            logger.warning(f"Layer '{name}' has {n_invalid} invalid geometries — repairing in-memory.")
            gdf.loc[invalid_mask, "geometry"] = gdf.loc[invalid_mask, "geometry"].apply(make_valid)

        _LAYER_CACHE[name] = gdf
        logger.info(f"Layer '{name}' loaded ({len(gdf)} features, CRS={gdf.crs}).")
        return gdf
    except Exception as e:
        logger.error(f"Failed to load GIS layer '{name}' from {filepath}: {e}")
        return None


def _is_pixel_coordinates(bounds) -> bool:
    """
    Return True if the bounding box looks like pixel (non-georeferenced) coordinates.

    Valid geographic coordinates satisfy ALL of:
        -180 <= x_min <= x_max <= 180
        -90  <= y_min <= y_max <= 90

    Any violation indicates pixel space or an unsupported CRS.
    """
    x_min, y_min, x_max, y_max = bounds
    return not (
        -180 <= x_min <= 180
        and -180 <= x_max <= 180
        and -90  <= y_min <= 90
        and -90  <= y_max <= 90
    )


def analyze_region_gis(region_geometry_geojson: dict) -> dict:
    """
    Perform spatial intersection of a detected region against available GIS layers.

    Args:
        region_geometry_geojson: A GeoJSON geometry dict (type + coordinates).
                                 Must be in EPSG:4326 to produce meaningful results.

    Returns a dict with keys:
        sensitive_zone       bool | None
        sensitive_zone_type  str  | None
        overlap_area_sq_m    float | None
        overlap_percentage   float | None
        gis_status           str   ('verified'|'no_intersection'|'non_georeferenced'|
                                    'unavailable'|'error')
        intersecting_layers  list[str]
    """
    _default = {
        "sensitive_zone":      None,
        "sensitive_zone_type": None,
        "overlap_area_sq_m":   None,
        "overlap_percentage":  None,
        "gis_status":          "unavailable",
        "intersecting_layers": [],
    }

    # ---- 1. Parse input geometry ----------------------------------------
    try:
        region_shape = shape(region_geometry_geojson)
        region_shape = make_valid(region_shape)
    except Exception as e:
        logger.error(f"Failed to parse input geometry: {e}")
        return {**_default, "gis_status": "error"}

    bounds = region_shape.bounds  # (x_min, y_min, x_max, y_max)
    if not bounds or len(bounds) != 4:
        return {**_default, "gis_status": "error"}

    # ---- 2. Non-georeferenced guard ------------------------------------
    if _is_pixel_coordinates(bounds):
        logger.info(f"Input geometry bounds {bounds} are outside valid lat/lon range — returning non_georeferenced.")
        return {**_default, "gis_status": "non_georeferenced"}

    # ---- 3. Discover available layers ----------------------------------
    available_layers = get_available_layers()
    if not available_layers:
        logger.warning("No GIS layer files found on disk.")
        return _default  # gis_status='unavailable'

    # ---- 4. Build a single-feature GeoDataFrame for the detection -------
    region_gdf = gpd.GeoDataFrame(geometry=[region_shape], crs="EPSG:4326")

    sensitive_zone   = False
    sensitive_types  = []
    total_overlap_m2 = 0.0

    # ---- 5. Per-layer intersection --------------------------------------
    for name, filepath in available_layers.items():
        layer_gdf = _load_layer(name, filepath)
        if layer_gdf is None:
            continue
        try:
            # CRS alignment — always reproject detection to match layer
            if layer_gdf.crs and layer_gdf.crs != region_gdf.crs:
                detection_proj = region_gdf.to_crs(layer_gdf.crs)
            else:
                detection_proj = region_gdf

            intersection = gpd.overlay(detection_proj, layer_gdf, how="intersection", keep_geom_type=False)
            if intersection.empty:
                continue

            sensitive_zone = True
            sensitive_types.append(name)

            # Area calculation — reproject to metric CRS (Web Mercator) for sq-metre output
            if intersection.crs and intersection.crs.is_geographic:
                area_gdf = intersection.to_crs("EPSG:3857")
            else:
                area_gdf = intersection
            total_overlap_m2 += float(area_gdf.geometry.area.sum())

        except Exception as e:
            logger.error(f"Error during GIS intersection with layer '{name}': {e}")
            continue

    # ---- 6. Region area (sq metres) ------------------------------------
    if region_gdf.crs and region_gdf.crs.is_geographic:
        region_area_m2 = float(region_gdf.to_crs("EPSG:3857").geometry.area.sum())
    else:
        region_area_m2 = float(region_gdf.geometry.area.sum())

    overlap_pct = (total_overlap_m2 / region_area_m2 * 100.0) if region_area_m2 > 0 else 0.0

    return {
        "sensitive_zone":      sensitive_zone,
        "sensitive_zone_type": ", ".join(sensitive_types) if sensitive_types else None,
        "overlap_area_sq_m":   round(total_overlap_m2, 2),
        "overlap_percentage":  round(min(overlap_pct, 100.0), 2),
        "gis_status":          "verified" if sensitive_zone else "no_intersection",
        "intersecting_layers": sensitive_types,
    }
