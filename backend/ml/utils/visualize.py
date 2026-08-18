import os
import numpy as np
import rasterio
from PIL import Image

def convert_oscd_scene_to_png(scene_path: str, output_path: str):
    """
    Reads B04 (Red), B03 (Green), and B02 (Blue) from an OSCD scene directory,
    performs robust contrast stretching, and saves as a PNG.
    """
    bands = ['B04.tif', 'B03.tif', 'B02.tif']
    arrays = []
    
    for band in bands:
        band_path = os.path.join(scene_path, band)
        if not os.path.exists(band_path):
            raise FileNotFoundError(f"Missing required band {band} in {scene_path}")
        
        with rasterio.open(band_path) as src:
            data = src.read(1)
            arrays.append(data)
            
    # Check dimensions match
    shape = arrays[0].shape
    for arr in arrays:
        if arr.shape != shape:
            raise ValueError(f"Band dimension mismatch in {scene_path}. Expected {shape}, got {arr.shape}")
            
    # Stack to shape (H, W, 3)
    rgb = np.stack(arrays, axis=-1).astype(np.float32)
    
    # Robust percentile-based contrast stretch (e.g. 2nd to 98th percentile)
    for i in range(3):
        band_data = rgb[..., i]
        p2, p98 = np.percentile(band_data[band_data > 0], (2, 98))
        # Avoid division by zero
        if p98 > p2:
            band_data = (band_data - p2) / (p98 - p2)
        else:
            band_data = np.zeros_like(band_data)
        
        # Clip and scale to 0-255
        band_data = np.clip(band_data, 0, 1) * 255.0
        rgb[..., i] = band_data
        
    rgb_uint8 = rgb.astype(np.uint8)
    
    # Ensure parent directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Save as PNG
    img = Image.fromarray(rgb_uint8)
    img.save(output_path, format="PNG")
    return output_path
