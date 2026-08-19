"""
ModelService — loads and runs the trained SiameseUNetAttention checkpoint.

Checkpoint: best_siamese_model.pth
Architecture: SiameseUNetAttention(in_channels=3) — RGB Sentinel-2
Training: 25 epochs, best F1 = 0.8365

Environment variables (set in backend/.env):
    SENTINEL2_MODEL_CHECKPOINT_PATH  — path to the .pth checkpoint
    LISS4_MODEL_CHECKPOINT_PATH      — path to LISS-4 checkpoint (optional)

The service is a singleton per sensor; the model is loaded once at startup
and kept in memory to avoid re-loading the 2.91 GB file on every request.
"""
import os
import torch
import numpy as np

from ..models.model import SiameseUNetAttention
from ..inference.postprocess import postprocess_mask
from ..geo.geojson import generate_geojson


# ---------------------------------------------------------------------------
# Default checkpoint path — relative to this file's location so it works
# without environment variables in development.
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(__file__)
_DEFAULT_S2_CKPT = os.path.join(_THIS_DIR, "..", "checkpoints", "best_siamese_model.pth")


class ModelService:
    """
    Loads a trained SiameseUNetAttention checkpoint and exposes a predict() method.

    The sentinel2 variant uses in_channels=3 (RGB: B04, B03, B02) to match
    the trained checkpoint best_siamese_model.pth whose first conv layer has
    shape [64, 3, 7, 7].
    """

    def __init__(self, sensor: str = "sentinel2", device=None):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.sensor = sensor.lower()

        # Resolve checkpoint paths from environment or defaults
        self.s2_checkpoint = os.environ.get(
            "SENTINEL2_MODEL_CHECKPOINT_PATH",
            os.path.normpath(_DEFAULT_S2_CKPT),
        )
        self.liss4_checkpoint = os.environ.get("LISS4_MODEL_CHECKPOINT_PATH", "")

        # --- Configurable inference threshold (TASK 1) ---
        # Reads SENTINEL2_INFERENCE_THRESHOLD from .env; defaults to 0.5 if absent/invalid.
        _raw_thresh = os.environ.get("SENTINEL2_INFERENCE_THRESHOLD", "0.5")
        try:
            _parsed = float(_raw_thresh)
            if 0.0 < _parsed <= 1.0:
                self.s2_threshold = _parsed
            else:
                print(f"[ModelService] WARNING: SENTINEL2_INFERENCE_THRESHOLD={_raw_thresh} out of (0,1]; defaulting to 0.5")
                self.s2_threshold = 0.5
        except (ValueError, TypeError):
            print(f"[ModelService] WARNING: Could not parse SENTINEL2_INFERENCE_THRESHOLD={_raw_thresh!r}; defaulting to 0.5")
            self.s2_threshold = 0.5

        self.s2_model = None
        self.liss4_model = None

        if self.sensor == "sentinel2":
            self._load_sentinel2()
        elif self.sensor == "liss4":
            self._load_liss4()
        else:
            raise ValueError(f"Unsupported sensor: {self.sensor!r}")

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _load_sentinel2(self):
        """
        Load the 3-channel RGB Sentinel-2 checkpoint.

        The checkpoint best_siamese_model.pth has:
            initial.0.weight: torch.Size([64, 3, 7, 7])
        so we instantiate SiameseUNetAttention(in_channels=3, pretrained=False).
        """
        if not self.s2_checkpoint or not os.path.exists(self.s2_checkpoint):
            raise FileNotFoundError(
                f"Trained change-detection checkpoint not found at: {self.s2_checkpoint!r}. "
                "Set SENTINEL2_MODEL_CHECKPOINT_PATH in your .env file."
            )

        print(f"[ModelService] Loading Sentinel-2 checkpoint: {self.s2_checkpoint}")
        print(f"[ModelService] Device: {self.device}")

        ckpt = torch.load(self.s2_checkpoint, map_location=self.device, weights_only=False)

        # Support both plain state_dict and rich checkpoint dict
        if isinstance(ckpt, dict) and "model_state_dict" in ckpt:
            state_dict = ckpt["model_state_dict"]
            epoch = ckpt.get("epoch", "?")
            best_f1 = ckpt.get("best_f1", None)
        else:
            state_dict = ckpt
            epoch = "?"
            best_f1 = None

        # Determine in_channels from the saved first conv weight
        first_conv_weight = state_dict.get("initial.0.weight")
        if first_conv_weight is None:
            raise ValueError(
                "Checkpoint is incompatible: 'initial.0.weight' key not found. "
                "Expected SiameseUNetAttention checkpoint."
            )
        in_channels = first_conv_weight.shape[1]  # [out, in, kH, kW]

        print(f"[ModelService] Checkpoint in_channels={in_channels}, epoch={epoch}"
              + (f", best_F1={best_f1:.4f}" if best_f1 is not None else ""))

        # Instantiate with correct in_channels (no pretrained weights — we load ours)
        self.s2_model = SiameseUNetAttention(pretrained=False, in_channels=in_channels)
        self.s2_model.load_state_dict(state_dict)
        self.s2_model.to(self.device)
        self.s2_model.eval()

        # Store in_channels for use in predict()
        self._s2_in_channels = in_channels
        print(f"[ModelService] Model loaded successfully. SiameseUNetAttention(in_channels={in_channels})")

    def _load_liss4(self):
        """Load a LISS-4 (3-band) checkpoint."""
        if not self.liss4_checkpoint or not os.path.exists(self.liss4_checkpoint):
            raise FileNotFoundError(
                "LISS-4 model checkpoint not configured or not found. "
                "Set LISS4_MODEL_CHECKPOINT_PATH in your .env file."
            )
        self.liss4_model = SiameseUNetAttention(pretrained=False, in_channels=3)

        ckpt = torch.load(self.liss4_checkpoint, map_location=self.device, weights_only=False)
        state_dict = ckpt["model_state_dict"] if isinstance(ckpt, dict) and "model_state_dict" in ckpt else ckpt
        self.liss4_model.load_state_dict(state_dict)
        self.liss4_model.to(self.device)
        self.liss4_model.eval()
        print(f"[ModelService] LISS-4 model loaded from {self.liss4_checkpoint}")

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict(self, before_path: str, after_path: str, threshold: float = None) -> dict:
        """
        Run inference on a before/after image pair.

        Args:
            before_path: Path to the BEFORE imagery directory (containing band TIFs)
                         or a single image file depending on sensor.
            after_path:  Path to the AFTER imagery directory.
            threshold:   Binary mask threshold on sigmoid probability.
                         Defaults to SENTINEL2_INFERENCE_THRESHOLD env-var (fallback 0.5).

        Returns:
            dict with keys: status, sensor, detection, regions, geojson,
                            probability_map_stats, mask_stats
        """
        if threshold is None:
            threshold = getattr(self, "s2_threshold", 0.5)
        if self.sensor == "sentinel2":
            return self._predict_sentinel2(before_path, after_path, threshold)
        elif self.sensor == "liss4":
            return self._predict_liss4(before_path, after_path, threshold)
        else:
            raise ValueError(f"Unsupported sensor: {self.sensor!r}")

    def _predict_sentinel2(self, before_path: str, after_path: str, threshold: float) -> dict:
        """
        Sentinel-2 inference handling both 13-channel native and 3-channel legacy checkpoints.
        """
        if self._s2_in_channels == 3:
            # ---------------------------------------------------------
            # DEVELOPER NOTE:
            # The currently supplied checkpoint is a 3-channel RGB model.
            # Because the original training dataset for this checkpoint could not 
            # be established as the OSCD 13-band pipeline, BhoomiDrishti uses an 
            # explicit legacy RGB compatibility adapter for demonstration/integration. 
            # A future production model should be retrained natively on the 13-band 
            # Sentinel-2 pipeline.
            # ---------------------------------------------------------
            print("[ModelService] Model input channels: 3")
            print("[ModelService] Preprocessing mode: legacy RGB compatibility")
            print(f"[ModelService] Inference threshold: {threshold}")
            from ..preprocessing.rgb_adapter import prepare_rgb_for_legacy_checkpoint
            try:
                img_a, shape_a, transform_a, crs_a = prepare_rgb_for_legacy_checkpoint(before_path)
                img_b, _, _, _ = prepare_rgb_for_legacy_checkpoint(after_path, target_shape=shape_a)
            except FileNotFoundError as e:
                raise ValueError(f"Invalid before/after satellite imagery: {e}") from e
            except Exception as e:
                raise ValueError(f"Before and after images could not be aligned: {e}") from e
        else:
            # Native 13-channel
            print(f"[ModelService] Model input channels: {self._s2_in_channels}")
            print("[ModelService] Preprocessing mode: native 13-channel Sentinel-2")
            from ..datasets.sentinel2_adapter import Sentinel2Adapter
            try:
                adapter = Sentinel2Adapter(before_path, after_path)
                img_a, img_b = adapter.load_and_align()
                shape_a = (img_a.shape[1], img_a.shape[2])
                transform_a = adapter.transform
                crs_a = adapter.crs
            except Exception as e:
                raise ValueError(f"Sentinel-2 13-channel data loading failed: {e}") from e

        _, h, w = img_a.shape  # (C, H, W)

        # --- Pad to multiple of 32 ---
        pad_h = (32 - h % 32) % 32
        pad_w = (32 - w % 32) % 32
        if pad_h > 0 or pad_w > 0:
            img_a = np.pad(img_a, ((0, 0), (0, pad_h), (0, pad_w)), mode="reflect")
            img_b = np.pad(img_b, ((0, 0), (0, pad_h), (0, pad_w)), mode="reflect")

        # --- Build tensors ---
        tensor_a = torch.from_numpy(img_a).unsqueeze(0).float().to(self.device)  # (1,3,H,W)
        tensor_b = torch.from_numpy(img_b).unsqueeze(0).float().to(self.device)

        # --- Forward pass ---
        model = self.s2_model
        with torch.inference_mode():
            logits = model(tensor_a, tensor_b)   # (1, 1, H, W)
            prob_map = torch.sigmoid(logits).squeeze().cpu().numpy()  # (H, W)

        # --- Crop back to original size ---
        prob_map = prob_map[:h, :w]

        # --- Probability map statistics ---
        prob_stats = {
            "min": float(prob_map.min()),
            "max": float(prob_map.max()),
            "mean": float(prob_map.mean()),
            "changed_pixels_above_threshold": int((prob_map > threshold).sum()),
            "total_pixels": int(prob_map.size),
            "pct_changed": float((prob_map > threshold).mean() * 100),
        }

        # --- Postprocess: thresholding + connected components ---
        binary_mask, components = postprocess_mask(prob_map, threshold=threshold)

        mask_stats = {
            "num_changed_pixels": int(binary_mask.sum()),
            "num_regions": len(components),
            "largest_region_px": max((c["pixel_count"] for c in components), default=0),
        }

        # --- GeoJSON (pixel-based for OSCD; georeferenced when CRS is available) ---
        resolution = 10.0  # Sentinel-2 B04 native resolution (metres)
        geojson_data = generate_geojson(binary_mask, transform_a, crs_a, components, resolution)

        # --- Aggregate confidence and area ---
        total_area = sum(f["properties"]["area_sq_m"] for f in geojson_data.get("features", []))
        overall_confidence = (
            sum(c["confidence"] for c in components) / len(components) if components else 0.0
        )

        return {
            "status": "detected" if components else "no_change",
            "sensor": "sentinel2",
            "checkpoint": os.path.basename(self.s2_checkpoint),
            "in_channels": self._s2_in_channels,
            "detection": {
                "confidence": overall_confidence,
                "area_sq_m": total_area,
            },
            "regions": components,
            "geojson": geojson_data,
            "probability_map_stats": prob_stats,
            "mask_stats": mask_stats,
        }

    def _predict_liss4(self, before_path: str, after_path: str, threshold: float) -> dict:
        from ..datasets import LISS4Adapter

        adapter = LISS4Adapter(before_path, after_path)
        img_a, img_b = adapter.load_and_align()
        img_a = adapter.normalize(img_a)
        img_b = adapter.normalize(img_b)

        _, h, w = img_a.shape
        pad_h = (32 - h % 32) % 32
        pad_w = (32 - w % 32) % 32
        if pad_h > 0 or pad_w > 0:
            img_a = np.pad(img_a, ((0, 0), (0, pad_h), (0, pad_w)), mode="reflect")
            img_b = np.pad(img_b, ((0, 0), (0, pad_h), (0, pad_w)), mode="reflect")

        tensor_a = torch.from_numpy(img_a).unsqueeze(0).float().to(self.device)
        tensor_b = torch.from_numpy(img_b).unsqueeze(0).float().to(self.device)

        with torch.inference_mode():
            logits = self.liss4_model(tensor_a, tensor_b)
            prob_map = torch.sigmoid(logits).squeeze().cpu().numpy()

        prob_map = prob_map[:h, :w]
        binary_mask, components = postprocess_mask(prob_map, threshold=threshold)
        geojson_data = generate_geojson(binary_mask, adapter.transform, adapter.crs, components, adapter.resolution)

        total_area = sum(f["properties"]["area_sq_m"] for f in geojson_data.get("features", []))
        overall_confidence = (
            sum(c["confidence"] for c in components) / len(components) if components else 0.0
        )

        return {
            "status": "detected" if components else "no_change",
            "sensor": "liss4",
            "checkpoint": os.path.basename(self.liss4_checkpoint),
            "detection": {"confidence": overall_confidence, "area_sq_m": total_area},
            "regions": components,
            "geojson": geojson_data,
        }


# ---------------------------------------------------------------------------
# Singleton registry — one model instance per sensor per process lifetime
# ---------------------------------------------------------------------------

_model_service_instances: dict[str, ModelService] = {}


def get_model_service(sensor: str = "sentinel2") -> ModelService:
    """
    Return (or lazily create) the singleton ModelService for the given sensor.
    The model is loaded once and kept in memory.
    """
    global _model_service_instances
    sensor = sensor.lower()
    if sensor not in _model_service_instances:
        try:
            _model_service_instances[sensor] = ModelService(sensor=sensor)
        except Exception as exc:
            raise RuntimeError(
                f"Model service failed to initialize for sensor={sensor!r}: {exc}"
            ) from exc
    return _model_service_instances[sensor]
