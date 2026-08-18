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
            state_dict = torch.load(checkpoint_path, map_location=self.device)
            self.model.load_state_dict(state_dict)
            print(f"Loaded model from {checkpoint_path}")
        else:
            raise FileNotFoundError("ML model checkpoint unavailable. Cannot run inference.")
            
    def predict(self, before_path, after_path, threshold=0.5):
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        from ml.preprocessing.transforms import read_and_align_bands, normalize_sentinel2_bands
        
        # 1. Authoritative Preprocessing Pipeline
        img_a_data, target_shape, transform_a, crs_a = read_and_align_bands(before_path)
        img_b_data, _, _, _ = read_and_align_bands(after_path, target_shape=target_shape)
        
        img_a_data = normalize_sentinel2_bands(img_a_data)
        img_b_data = normalize_sentinel2_bands(img_b_data)
        
        # 2. Determine padding to make dimensions divisible by 32 (U-Net requirement)
        _, h, w = img_a_data.shape
        pad_h = (32 - (h % 32)) % 32
        pad_w = (32 - (w % 32)) % 32
        
        if pad_h > 0 or pad_w > 0:
            img_a_data = np.pad(img_a_data, ((0,0), (0, pad_h), (0, pad_w)), mode='reflect')
            img_b_data = np.pad(img_b_data, ((0,0), (0, pad_h), (0, pad_w)), mode='reflect')
            
        tensor_a = torch.from_numpy(img_a_data).unsqueeze(0).to(self.device)
        tensor_b = torch.from_numpy(img_b_data).unsqueeze(0).to(self.device)
        
        # 3. Model Forward Pass
        with torch.no_grad():
            logits = self.model(tensor_a, tensor_b)
            prob_map = torch.sigmoid(logits).cpu().numpy()[0, 0]
            
        # 4. Crop back to exact original size
        prob_map = prob_map[:h, :w]
        
        # 5. Postprocess (Connected Components)
        binary_mask, components = postprocess_mask(prob_map, threshold=threshold)
        
        # 6. Geospatial Translation
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
        checkpoint_path = os.environ.get("MODEL_CHECKPOINT_PATH", os.path.join(os.path.dirname(__file__), "..", "models", "best_model.pth"))
        try:
            model_service_instance = ModelService(checkpoint_path=checkpoint_path, in_channels=13)
        except Exception as e:
            # We delay the throw to the API layer if needed, or throw it here
            raise RuntimeError(f"Model service failed to initialize: {str(e)}")
    return model_service_instance
