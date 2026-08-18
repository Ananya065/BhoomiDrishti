import numpy as np
import rasterio
import os
from .satellite_dataset import SatelliteImagePair

class LISS4Adapter(SatelliteImagePair):
    """
    Adapter for LISS-4 imagery.
    LISS-4 typically has 3 bands (Green, Red, NIR) at 5.8m resolution.
    """
    @property
    def sensor_name(self) -> str:
        return "liss4"
        
    def load_and_align(self) -> tuple[np.ndarray, np.ndarray]:
        # Typically LISS-4 comes as a single multi-band GeoTIFF per scene rather than separate band files.
        # This checks if it's a directory (like OSCD) or a file.
        
        def load_image(path):
            if os.path.isdir(path):
                # Fallback if given a directory - look for a .tif file
                tifs = [f for f in os.listdir(path) if f.endswith('.tif')]
                if not tifs:
                    raise ValueError(f"No GeoTIFF found in {path}")
                path = os.path.join(path, tifs[0])
                
            with rasterio.open(path) as src:
                data = src.read()
                transform = src.transform
                crs = src.crs
            return data, transform, crs
            
        self.before_data, self.transform, self.crs = load_image(self.before_path)
        self.after_data, _, _ = load_image(self.after_path)
        self.resolution = 5.8 # LISS-4 resolution
        
        # Ensure dimensions match
        # Basic alignment for LISS-4 (assuming they are already aligned or same size for now)
        if self.before_data.shape != self.after_data.shape:
            # Simple padding/cropping to match before_data shape
            # In a real production system, we'd use rasterio.vrt.WarpedVRT to align
            c, h, w = self.before_data.shape
            self.after_data = self.after_data[:, :h, :w]
            
        return self.before_data, self.after_data

    def normalize(self, data: np.ndarray) -> np.ndarray:
        # LISS-4 normalization. LISS-4 data is typically 10-bit or 16-bit.
        # We normalize to 0-1 range.
        data = data.astype('float32')
        # Simple percentiles or max value normalization
        # Using 1023 as max for 10-bit as a placeholder
        data = np.clip(data / 1023.0, 0, 1)
        return data
