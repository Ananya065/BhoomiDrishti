"""
RGB-only Sentinel-2 inference adapter.

The trained checkpoint best_siamese_model.pth was trained on 3-channel RGB
images extracted from Sentinel-2 (B04=Red, B03=Green, B02=Blue), normalized
to [0,1] by dividing by 10000.

This adapter reads only those three bands so the tensor shape matches the
checkpoint's initial.0.weight: [64, 3, 7, 7].
"""
import os
import numpy as np
import rasterio
from rasterio.enums import Resampling


# Band order used during training: B04 (Red), B03 (Green), B02 (Blue)
RGB_BANDS = ["B04.tif", "B03.tif", "B02.tif"]


def load_rgb_sentinel2(band_dir: str, target_shape=None):
    """
    Load and optionally resample Sentinel-2 RGB bands (B04, B03, B02).

    Returns:
        image  : np.ndarray float32, shape (3, H, W), values in [0, 1]
        shape  : (H, W) tuple
        transform: rasterio affine transform of B04
        crs    : CRS of B04
    """
    # Use B04 as the reference resolution grid (10 m)
    ref_path = os.path.join(band_dir, "B04.tif")
    if not os.path.exists(ref_path):
        raise FileNotFoundError(f"B04.tif not found in {band_dir}")

    with rasterio.open(ref_path) as ref:
        ref_shape = (ref.height, ref.width)
        ref_transform = ref.transform
        ref_crs = ref.crs
        if target_shape is None:
            target_shape = ref_shape

    bands = []
    for band_name in RGB_BANDS:
        path = os.path.join(band_dir, band_name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"{band_name} not found in {band_dir}")
        with rasterio.open(path) as src:
            if (src.height, src.width) == target_shape:
                data = src.read(1).astype(np.float32)
            else:
                data = src.read(
                    1,
                    out_shape=target_shape,
                    resampling=Resampling.bilinear,
                ).astype(np.float32)
        bands.append(data)

    image = np.stack(bands, axis=0)  # (3, H, W)
    # Normalize: Sentinel-2 Level-2A reflectance scaled by 10000
    image = np.clip(image / 10000.0, 0.0, 1.0)
    return image, target_shape, ref_transform, ref_crs
