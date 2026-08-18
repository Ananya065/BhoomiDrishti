"""
Service layer for orchestrating classification of changed regions.
"""
import os
import rasterio
import numpy as np
from PIL import Image
from typing import List, Dict, Any

from backend.ml.classification.classifier import classify_image

def _read_band(base_path: str, band_name: str) -> np.ndarray:
    """Reads a single band from the OSCD directory format."""
    band_path = os.path.join(base_path, f"{band_name}.tif")
    if not os.path.exists(band_path):
        raise FileNotFoundError(f"Band file not found: {band_path}")
    with rasterio.open(band_path) as src:
        return src.read(1)

def _get_rgb_crop(after_path: str, bbox: List[int]) -> Image.Image:
    """
    Reads R, G, B bands from the after_path, stacks them, crops to bbox,
    and returns a PIL Image.
    bbox format: [x, y, w, h]
    """
    x, y, w, h = bbox
    
    # Read R, G, B (B04, B03, B02)
    b04 = _read_band(after_path, 'B04')
    b03 = _read_band(after_path, 'B03')
    b02 = _read_band(after_path, 'B02')
    
    # Crop
    r_crop = b04[y:y+h, x:x+w]
    g_crop = b03[y:y+h, x:x+w]
    b_crop = b02[y:y+h, x:x+w]
    
    # Stack to shape (H, W, 3)
    rgb = np.stack([r_crop, g_crop, b_crop], axis=-1)
    
    # Normalize to 0-255 based on percentiles for better contrast
    p2, p98 = np.percentile(rgb, (2, 98))
    if p98 > p2:
        rgb = np.clip((rgb - p2) / (p98 - p2), 0, 1)
    else:
        max_val = np.max(rgb)
        if max_val > 0:
            rgb = rgb / max_val
    
    rgb = (rgb * 255).astype(np.uint8)
    return Image.fromarray(rgb)

def classify_regions(before_path: str, after_path: str, components: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Classifies a list of changed regions.
    """
    results = []
    for comp in components:
        bbox = comp.get('bbox')
        if not bbox:
            results.append({
                'activity_type': 'unknown',
                'classification_status': 'error',
                'classification_method': 'clip_zero_shot'
            })
            continue
            
        try:
            image_crop = _get_rgb_crop(after_path, bbox)
            class_res = classify_image(image_crop)
            results.append(class_res)
        except Exception as e:
            results.append({
                'activity_type': 'unknown',
                'classification_status': 'unavailable',
                'classification_method': 'clip_zero_shot',
                'error_msg': str(e)
            })
            
    return results
