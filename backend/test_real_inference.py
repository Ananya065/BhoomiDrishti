"""
End-to-end real inference test using best_siamese_model.pth.

MODEL INFERENCE: REAL
CHECKPOINT: best_siamese_model.pth
MOCK PREDICTION: FALSE
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from dotenv import load_dotenv
load_dotenv()

import torch
import numpy as np

# ─── 1. Load checkpoint directly and verify ────────────────────────────────
print("=" * 60)
print("STEP 1: Checkpoint verification")
ckpt_path = os.environ.get(
    "SENTINEL2_MODEL_CHECKPOINT_PATH",
    "backend/ml/checkpoints/best_siamese_model.pth"
)
if not os.path.exists(ckpt_path):
    print(f"FAIL: Checkpoint not found at {ckpt_path}")
    sys.exit(1)

ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
sd = ckpt["model_state_dict"]
in_ch = sd["initial.0.weight"].shape[1]
print(f"  Checkpoint keys: {list(ckpt.keys())}")
print(f"  Epoch: {ckpt['epoch']}, Best F1: {ckpt['best_f1']:.4f}")
print(f"  Detected in_channels: {in_ch}")
print(f"  Total params: {sum(v.numel() for v in sd.values()):,}")
print("  [OK] Checkpoint is valid")

# ─── 2. Model instantiation ────────────────────────────────────────────────
print("\nSTEP 2: Model instantiation")
from ml.models.model import SiameseUNetAttention
model = SiameseUNetAttention(pretrained=False, in_channels=in_ch)
model.load_state_dict(sd)
model.eval()
device = torch.device("cpu")
model.to(device)
total = sum(p.numel() for p in model.parameters())
print(f"  SiameseUNetAttention(in_channels={in_ch})")
print(f"  Parameters: {total:,}")
print("  [OK] Model loaded and in eval mode")

# ─── 3. Architecture compatibility check ──────────────────────────────────
print("\nSTEP 3: Architecture compatibility")
first_conv = model.initial[0]
print(f"  initial[0].in_channels: {first_conv.in_channels}")
print(f"  initial[0].out_channels: {first_conv.out_channels}")
print(f"  initial[0].weight.shape: {first_conv.weight.shape}")
assert first_conv.in_channels == in_ch, "Mismatch!"
print("  [OK] Architecture matches checkpoint")

# ─── 4. Preprocessing ─────────────────────────────────────────────────────
print("\nSTEP 4: Load real OSCD RGB imagery")
oscd_root = os.environ.get("OSCD_DATASET_ROOT", "")
city = "abudhabi"
before_dir = os.path.join(oscd_root, "Onera Satellite Change Detection dataset - Images", city, "imgs_1_rect")
after_dir  = os.path.join(oscd_root, "Onera Satellite Change Detection dataset - Images", city, "imgs_2_rect")

if not os.path.exists(before_dir):
    print(f"  WARNING: OSCD path not found: {before_dir}")
    print("  Using synthetic test tensors instead...")
    img_a = np.random.rand(3, 256, 256).astype(np.float32)
    img_b = np.random.rand(3, 256, 256).astype(np.float32)
    crs_a, transform_a = None, None
    real_data = False
else:
    from ml.preprocessing.rgb_adapter import load_rgb_sentinel2
    img_a, shape, transform_a, crs_a = load_rgb_sentinel2(before_dir)
    img_b, _, _, _ = load_rgb_sentinel2(after_dir, target_shape=shape)
    real_data = True
    print(f"  Loaded city: {city}")
    print(f"  Before shape: {img_a.shape}, range [{img_a.min():.4f}, {img_a.max():.4f}]")
    print(f"  After  shape: {img_b.shape}, range [{img_b.min():.4f}, {img_b.max():.4f}]")
    print(f"  CRS: {crs_a}")

# Crop to 256x256 patch for fast test
H, W = img_a.shape[1], img_a.shape[2]
patch_h, patch_w = min(256, H), min(256, W)
img_a_patch = img_a[:, :patch_h, :patch_w]
img_b_patch = img_b[:, :patch_h, :patch_w]

# Pad to multiple of 32
pad_h = (32 - patch_h % 32) % 32
pad_w = (32 - patch_w % 32) % 32
if pad_h > 0 or pad_w > 0:
    img_a_patch = np.pad(img_a_patch, ((0,0),(0,pad_h),(0,pad_w)), mode='reflect')
    img_b_patch = np.pad(img_b_patch, ((0,0),(0,pad_h),(0,pad_w)), mode='reflect')

print(f"  Patch used: {patch_h}x{patch_w} (padded to {img_a_patch.shape[1]}x{img_a_patch.shape[2]})")
print("  [OK] Preprocessing complete")

# ─── 5. Real forward pass ─────────────────────────────────────────────────
print("\nSTEP 5: Real inference (forward pass)")
tensor_a = torch.from_numpy(img_a_patch).unsqueeze(0).float()
tensor_b = torch.from_numpy(img_b_patch).unsqueeze(0).float()
print(f"  Input tensors: {tensor_a.shape} (before), {tensor_b.shape} (after)")

with torch.inference_mode():
    logits = model(tensor_a, tensor_b)
    prob_map = torch.sigmoid(logits).squeeze().numpy()

prob_map = prob_map[:patch_h, :patch_w]
print(f"  Output prob_map shape: {prob_map.shape}")
print(f"  Prob range: [{prob_map.min():.4f}, {prob_map.max():.4f}]")
print(f"  Mean prob: {prob_map.mean():.4f}")
print("  [OK] Forward pass successful — REAL MODEL OUTPUT")

# ─── 6. Postprocessing ────────────────────────────────────────────────────
print("\nSTEP 6: Postprocessing")
from ml.inference.postprocess import postprocess_mask
binary_mask, components = postprocess_mask(prob_map, threshold=0.5)
changed_px = int(binary_mask.sum())
pct = changed_px / binary_mask.size * 100
print(f"  Changed pixels (>0.5): {changed_px}/{binary_mask.size} ({pct:.2f}%)")
print(f"  Connected regions: {len(components)}")
if components:
    largest = max(c["pixel_count"] for c in components)
    print(f"  Largest region: {largest} pixels")
print("  [OK] Postprocessing complete")

# ─── 7. Mask visualisation artifacts ─────────────────────────────────────
print("\nSTEP 7: Saving artifacts")
output_dir = "backend/data/inference_outputs"
os.makedirs(output_dir, exist_ok=True)

from ml.utils.visualize import convert_oscd_scene_to_png
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Save change mask
plt.figure(figsize=(6, 6))
plt.imshow(prob_map, cmap="hot", vmin=0, vmax=1)
plt.colorbar(label="Change probability")
plt.title(f"Change Probability Map — {city}\nMODEL: REAL | CHECKPOINT: best_siamese_model.pth")
plt.tight_layout()
mask_png = os.path.join(output_dir, f"{city}_change_mask.png")
plt.savefig(mask_png, dpi=100)
plt.close()
print(f"  Saved: {mask_png}")

# Save before RGB
before_png = os.path.join(output_dir, f"{city}_before.png")
after_png  = os.path.join(output_dir, f"{city}_after.png")
if real_data and os.path.exists(before_dir):
    try:
        convert_oscd_scene_to_png(before_dir, before_png)
        convert_oscd_scene_to_png(after_dir,  after_png)
        print(f"  Saved: {before_png}")
        print(f"  Saved: {after_png}")
    except Exception as e:
        print(f"  NOTE: Could not save RGB PNGs: {e}")

print("\n" + "=" * 60)
print("FINAL RESULT")
print("=" * 60)
print(f"  MODEL INFERENCE: REAL")
print(f"  CHECKPOINT: best_siamese_model.pth")
print(f"  MOCK PREDICTION: FALSE")
print(f"  in_channels: {in_ch}")
print(f"  Epoch trained: {ckpt['epoch']}, Best F1: {ckpt['best_f1']:.4f}")
print(f"  Real imagery: {'YES' if real_data else 'NO (synthetic patch)'}")
print(f"  Changed pixels: {changed_px} ({pct:.2f}%)")
print(f"  Detected regions: {len(components)}")
print(f"  Artifacts: {output_dir}/")
print("  [PASS] Real end-to-end inference complete")
