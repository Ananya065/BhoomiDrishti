import numpy as np
from .satellite_dataset import SatelliteImagePair

class Sentinel2Adapter(SatelliteImagePair):
    """
    Adapter for 13-band Sentinel-2 imagery.
    """
    @property
    def sensor_name(self) -> str:
        return "sentinel2"
        
    def load_and_align(self) -> tuple[np.ndarray, np.ndarray]:
        from ..preprocessing.transforms import read_and_align_bands
        
        img_a_data, target_shape, transform_a, crs_a = read_and_align_bands(self.before_path)
        img_b_data, _, _, _ = read_and_align_bands(self.after_path, target_shape=target_shape)
        
        self.crs = crs_a
        self.transform = transform_a
        self.resolution = 10.0 # Sentinel-2 B04 resolution
        self.metadata = {
            "target_shape": target_shape
        }
        
        self.before_data = img_a_data
        self.after_data = img_b_data
        
        return img_a_data, img_b_data

    def normalize(self, data: np.ndarray) -> np.ndarray:
        from ..preprocessing.transforms import normalize_sentinel2_bands
        return normalize_sentinel2_bands(data)
