import os
from typing import Dict

GIS_DATA_ROOT = os.environ.get('GIS_DATA_ROOT', 'data/gis')

LAYER_CONFIG = {
    'forest': 'forest.geojson',
    'protected_area': 'protected_area.geojson',
    'water_body': 'water_body.geojson',
    'wetland': 'wetland.geojson',
    'agricultural': 'agricultural.geojson'
}

def get_available_layers() -> Dict[str, str]:
    """Check which GIS layer files actually exist and return a dict of name -> path."""
    available = {}
    for name, filename in LAYER_CONFIG.items():
        filepath = os.path.join(GIS_DATA_ROOT, filename)
        if os.path.exists(filepath):
            available[name] = filepath
    return available
