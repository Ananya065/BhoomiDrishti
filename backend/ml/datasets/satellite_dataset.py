from abc import ABC, abstractmethod
import numpy as np

class SatelliteImagePair(ABC):
    """
    Abstract representation of a before/after satellite image pair.
    """
    def __init__(self, before_path: str, after_path: str):
        self.before_path = before_path
        self.after_path = after_path
        self.before_data = None
        self.after_data = None
        self.metadata = {}
        self.crs = None
        self.transform = None
        self.resolution = None
        
    @property
    @abstractmethod
    def sensor_name(self) -> str:
        pass

    @abstractmethod
    def load_and_align(self) -> tuple[np.ndarray, np.ndarray]:
        """
        Loads the before and after images, aligns them spatially if needed,
        and returns them as (channels, height, width) numpy arrays.
        """
        pass
        
    @abstractmethod
    def normalize(self, data: np.ndarray) -> np.ndarray:
        """
        Applies sensor-specific normalization.
        """
        pass
