import numpy as np
import rasterio
from rasterio.enums import Resampling

def normalize_sentinel2_bands(image_stack):
    """
    Normalizes a stack of Sentinel-2 bands (13 channels).
    Assumes standard Level-2A surface reflectance scaled by 10000.
    Returns array in range [0, 1].
    """
    # Image statistics confirm values are integer scaled by 10000
    image = image_stack.astype(np.float32) / 10000.0
    image = np.clip(image, 0.0, 1.0)
    return image

def read_and_align_bands(directory, target_shape=None, target_transform=None, target_crs=None, is_mask=False):
    """
    Reads all 13 Sentinel-2 bands, resampling them to a target_shape if necessary.
    If target_shape is not provided, uses B04 (10m) as the target resolution grid.
    is_mask: If True, uses nearest neighbor resampling (for labels). Otherwise uses bilinear.
    """
    band_names = ["B01.tif", "B02.tif", "B03.tif", "B04.tif", "B05.tif", "B06.tif", 
                  "B07.tif", "B08.tif", "B8A.tif", "B09.tif", "B10.tif", "B11.tif", "B12.tif"]
    
    resampling_method = Resampling.nearest if is_mask else Resampling.bilinear
    
    import os
    # Determine target resolution from 10m band (B04) if not provided
    if target_shape is None:
        b04_path = os.path.join(directory, "B04.tif")
        # Fallback to B01 if B04 doesn't exist for some reason
        if not os.path.exists(b04_path):
            b04_path = os.path.join(directory, "B01.tif")
            
        with rasterio.open(b04_path) as src:
            target_shape = (src.height, src.width)
            target_transform = src.transform
            target_crs = src.crs

    bands = []
    for b in band_names:
        path = os.path.join(directory, b)
        with rasterio.open(path) as src:
            if (src.height, src.width) == target_shape:
                data = src.read(1)
            else:
                # Resample to target grid
                data = src.read(
                    1,
                    out_shape=target_shape,
                    resampling=resampling_method
                )
            bands.append(data)
            
    # Stack to shape (13, H, W)
    image = np.stack(bands, axis=0)
    return image, target_shape, target_transform, target_crs
