import os
import logging
from functools import lru_cache
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# GIS_DATA_ROOT — read from environment, with a sensible default.
# For local Windows dev, set this in backend/.env:
#   GIS_DATA_ROOT=C:/Users/adity/OneDrive/Desktop/bhoomidrishti/backend/data/gis
# ---------------------------------------------------------------------------
GIS_DATA_ROOT = os.environ.get("GIS_DATA_ROOT", "data/gis")

# ---------------------------------------------------------------------------
# Layer config — maps logical layer names to filenames inside GIS_DATA_ROOT.
# Override individual layer filenames via environment variables.
# ---------------------------------------------------------------------------
LAYER_CONFIG: Dict[str, str] = {
    "protected_area": os.environ.get("PROTECTED_AREA_LAYER", "india_protected_areas.geojson"),
    "water_body":     os.environ.get("WATER_LAYER",          "all_india_water.geojson"),
    "forest":         os.environ.get("FOREST_LAYER",         "forest.geojson"),
}


def get_available_layers() -> Dict[str, str]:
    """Return a dict of {layer_name: absolute_path} for every layer file that exists on disk."""
    available: Dict[str, str] = {}
    for name, filename in LAYER_CONFIG.items():
        filepath = os.path.join(GIS_DATA_ROOT, filename)
        if os.path.exists(filepath):
            available[name] = filepath
        else:
            logger.debug(f"GIS layer '{name}' not found at {filepath} — skipping.")
    return available
