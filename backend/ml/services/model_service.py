import os
import torch
import numpy as np
import rasterio
from ..models.model import SiameseUNetAttention
from ..inference.postprocess import postprocess_mask
from ..geo.geojson import generate_geojson

class ModelService:
    def __init__(self, checkpoint_path=None, device=None, in_channels=13):
        self.device = device if device else torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.in_channels = in_channels
        self.model = SiameseUNetAttention(pretrained=False, in_channels=in_channels)
        self.model.to(self.device)
        self.model.eval()
        
        if checkpoint_path and os.path.exists(checkpoint_path):
            self.model.load_state_dict(torch.load(checkpoint_path, map_location=self.device))
            print(f"Loaded model from {checkpoint_path}")
        else:
            print("Warning: No checkpoint loaded. Model will output random predictions.")
            
    def _load_and_preprocess_image(self, file_path):
        """Loads an image (stacked TIF or directory of bands) and preprocesses it."""
        if os.path.isdir(file_path):
            band_names = ["B01.tif", "B02.tif", "B03.tif", "B04.tif", "B05.tif", "B06.tif", 
                          "B07.tif", "B08.tif", "B8A.tif", "B09.tif", "B10.tif", "B11.tif", "B12.tif"]
            bands = []
            transform = None
            crs = None
            for i, b in enumerate(band_names):
                path = os.path.join(file_path, b)
                with rasterio.open(path) as src:
                    if i == 0:
                        transform = src.transform
                        crs = src.crs
                    bands.append(src.read(1))
            data = np.stack(bands, axis=0) # (13, H, W)
        else:
            with rasterio.open(file_path) as src:
                data = src.read() # (C, H, W)
                transform = src.transform
                crs = src.crs
            
        # Select first `in_channels` bands if there are more, or pad if fewer
        if data.shape[0] > self.in_channels:
            data = data[:self.in_channels, :, :]
        elif data.shape[0] < self.in_channels:
            pad = np.zeros((self.in_channels - data.shape[0], data.shape[1], data.shape[2]), dtype=data.dtype)
            data = np.concatenate([data, pad], axis=0)
            
        # Normalize
        data = data.astype(np.float32) / 10000.0
        data = np.clip(data, 0.0, 1.0)
        
        return data, transform, crs

    def predict(self, before_path, after_path, threshold=0.5):
        img_a_data, transform_a, crs_a = self._load_and_preprocess_image(before_path)
        img_b_data, _, _ = self._load_and_preprocess_image(after_path)
        
        # Determine padding to make dimensions divisible by 32 (U-Net requirement)
        _, h, w = img_a_data.shape
        pad_h = (32 - (h % 32)) % 32
        pad_w = (32 - (w % 32)) % 32
        
        if pad_h > 0 or pad_w > 0:
            img_a_data = np.pad(img_a_data, ((0,0), (0, pad_h), (0, pad_w)), mode='reflect')
            img_b_data = np.pad(img_b_data, ((0,0), (0, pad_h), (0, pad_w)), mode='reflect')
            
        tensor_a = torch.from_numpy(img_a_data).unsqueeze(0).to(self.device)
        tensor_b = torch.from_numpy(img_b_data).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            logits = self.model(tensor_a, tensor_b)
            prob_map = torch.sigmoid(logits).cpu().numpy()[0, 0]
            
        # Crop back to original size
        prob_map = prob_map[:h, :w]
        
        # Postprocess
        binary_mask, components = postprocess_mask(prob_map, threshold=threshold)
        
        # Geospatial
        geojson_data = generate_geojson(binary_mask, transform_a, crs_a, components)
        
        # Compute total area
        total_area = sum(f["properties"]["area_sq_m"] for f in geojson_data["features"])
        # Overall confidence
        if components:
            overall_confidence = sum(c["confidence"] for c in components) / len(components)
        else:
            overall_confidence = 0.0
            
        return {
            "status": "detected",
            "detection": {
                "confidence": overall_confidence,
                "area_sq_m": total_area
            },
            "regions": components,
            "geojson": geojson_data
        }

model_service_instance = None

def get_model_service():
    global model_service_instance
    if model_service_instance is None:
        # We can configure this path from env vars
        checkpoint_path = os.path.join(os.path.dirname(__file__), "..", "models", "best_model.pth")
        model_service_instance = ModelService(checkpoint_path=checkpoint_path, in_channels=13)
    return model_service_instance
