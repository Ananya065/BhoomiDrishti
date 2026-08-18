import os
import torch
import numpy as np
from ..models.model import SiameseUNetAttention
from ..inference.postprocess import postprocess_mask
from ..geo.geojson import generate_geojson
from ..datasets import Sentinel2Adapter, LISS4Adapter

class ModelService:
    def __init__(self, sensor="sentinel2", device=None):
        self.device = device if device else torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.sensor = sensor.lower()
        
        # Load configuration
        self.s2_checkpoint = os.environ.get("SENTINEL2_MODEL_CHECKPOINT_PATH", os.path.join(os.path.dirname(__file__), "..", "models", "best_model.pth"))
        self.liss4_checkpoint = os.environ.get("LISS4_MODEL_CHECKPOINT_PATH", "")
        
        # Model placeholders
        self.s2_model = None
        self.liss4_model = None
        
        if self.sensor == "sentinel2":
            self._load_sentinel2()
        elif self.sensor == "liss4":
            self._load_liss4()
        else:
            raise ValueError(f"Unsupported sensor: {self.sensor}")
            
    def _load_sentinel2(self):
        self.s2_model = SiameseUNetAttention(pretrained=False, in_channels=13)
        self.s2_model.to(self.device)
        self.s2_model.eval()
        
        if self.s2_checkpoint and os.path.exists(self.s2_checkpoint):
            ckpt = torch.load(self.s2_checkpoint, map_location=self.device)
            # Handle both legacy raw state_dict and rich checkpoint dict
            state_dict = ckpt["model_state_dict"] if isinstance(ckpt, dict) and "model_state_dict" in ckpt else ckpt
            self.s2_model.load_state_dict(state_dict)
            if isinstance(ckpt, dict) and "epoch" in ckpt:
                print(f"Loaded Sentinel-2 model from {self.s2_checkpoint} (epoch={ckpt['epoch']}, val_f1={ckpt.get('val_f1', 'n/a'):.4f})")
            else:
                print(f"Loaded Sentinel-2 model from {self.s2_checkpoint}")
        else:
            raise FileNotFoundError("Sentinel-2 ML model checkpoint unavailable. Cannot run inference.")

    def _load_liss4(self):
        if not self.liss4_checkpoint or not os.path.exists(self.liss4_checkpoint):
            raise FileNotFoundError("LISS-4 model checkpoint not configured.")
            
        # Assuming LISS-4 uses 3 bands (in_channels=3)
        self.liss4_model = SiameseUNetAttention(pretrained=False, in_channels=3)
        self.liss4_model.to(self.device)
        self.liss4_model.eval()
        state_dict = torch.load(self.liss4_checkpoint, map_location=self.device)
        self.liss4_model.load_state_dict(state_dict)
        print(f"Loaded LISS-4 model from {self.liss4_checkpoint}")
            
    def predict(self, before_path, after_path, threshold=0.5):
        # 1. Authoritative Preprocessing Pipeline using Adapters
        if self.sensor == "sentinel2":
            adapter = Sentinel2Adapter(before_path, after_path)
            model = self.s2_model
        elif self.sensor == "liss4":
            adapter = LISS4Adapter(before_path, after_path)
            model = self.liss4_model
        else:
            raise ValueError(f"Unsupported sensor: {self.sensor}")
            
        img_a_data, img_b_data = adapter.load_and_align()
        
        img_a_data = adapter.normalize(img_a_data)
        img_b_data = adapter.normalize(img_b_data)
        
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
            logits = model(tensor_a, tensor_b)
            prob_map = torch.sigmoid(logits).cpu().numpy()[0, 0]
            
        # 4. Crop back to exact original size
        prob_map = prob_map[:h, :w]
        
        # 5. Postprocess (Connected Components)
        binary_mask, components = postprocess_mask(prob_map, threshold=threshold)
        
        # 6. Geospatial Translation
        geojson_data = generate_geojson(binary_mask, adapter.transform, adapter.crs, components, adapter.resolution)
        
        # Compute total area
        total_area = sum(f["properties"]["area_sq_m"] for f in geojson_data["features"])
        # Overall confidence
        if components:
            overall_confidence = sum(c["confidence"] for c in components) / len(components)
        else:
            overall_confidence = 0.0
            
        return {
            "status": "detected",
            "sensor": self.sensor,
            "detection": {
                "confidence": overall_confidence,
                "area_sq_m": total_area
            },
            "regions": components,
            "geojson": geojson_data
        }

model_service_instances = {}

def get_model_service(sensor="sentinel2"):
    global model_service_instances
    sensor = sensor.lower()
    if sensor not in model_service_instances:
        try:
            model_service_instances[sensor] = ModelService(sensor=sensor)
        except Exception as e:
            raise RuntimeError(f"Model service failed to initialize for sensor {sensor}: {str(e)}")
    return model_service_instances[sensor]
