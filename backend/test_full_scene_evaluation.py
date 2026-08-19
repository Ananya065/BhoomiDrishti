import sys, os
import torch
import numpy as np
import rasterio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import cv2
from dotenv import load_dotenv

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
load_dotenv()

def compute_metrics(pred_mask, gt_mask):
    """Compute precision, recall, f1, and iou."""
    # Ensure boolean
    pred = pred_mask.astype(bool)
    gt = gt_mask.astype(bool)
    
    tp = np.sum(pred & gt)
    fp = np.sum(pred & ~gt)
    fn = np.sum(~pred & gt)
    
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    iou = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0.0
    
    return precision, recall, f1, iou

def main():
    print("=" * 60)
    print("STEP 1: Load Environment & Configuration")
    ckpt_path = os.environ.get(
        "SENTINEL2_MODEL_CHECKPOINT_PATH", 
        "backend/ml/checkpoints/best_siamese_model.pth"
    )
    oscd_root = os.environ.get("OSCD_DATASET_ROOT", "")
    
    if not os.path.exists(ckpt_path):
        print(f"FAIL: Checkpoint not found at {ckpt_path}")
        sys.exit(1)
    if not oscd_root or not os.path.exists(oscd_root):
        print(f"FAIL: OSCD_DATASET_ROOT not found at {oscd_root}")
        sys.exit(1)
        
    print(f"  Checkpoint: {ckpt_path}")
    print(f"  OSCD Root: {oscd_root}")

    print("\nSTEP 2: Load Model")
    from ml.models.model import SiameseUNetAttention
    
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    sd = ckpt["model_state_dict"] if "model_state_dict" in ckpt else ckpt
    in_channels = sd["initial.0.weight"].shape[1]
    
    model = SiameseUNetAttention(pretrained=False, in_channels=in_channels)
    model.load_state_dict(sd)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.eval()
    print(f"  Model loaded: SiameseUNetAttention(in_channels={in_channels}) on {device}")
    
    print("\nSTEP 3: Load Full Scene & Ground Truth (Abu Dhabi)")
    city = "abudhabi"
    before_dir = os.path.join(oscd_root, "Onera Satellite Change Detection dataset - Images", city, "imgs_1_rect")
    after_dir  = os.path.join(oscd_root, "Onera Satellite Change Detection dataset - Images", city, "imgs_2_rect")
    
    from ml.preprocessing.rgb_adapter import prepare_rgb_for_legacy_checkpoint
    img_a, shape_a, trans_a, crs_a = prepare_rgb_for_legacy_checkpoint(before_dir)
    img_b, _, _, _ = prepare_rgb_for_legacy_checkpoint(after_dir, target_shape=shape_a)
    
    _, H, W = img_a.shape
    print(f"  Scene size: {W} x {H}")
    print("  Preprocessing: Legacy RGB Compatibility mode (divided by 255.0)")
    
    # Ground truth
    gt_path = os.path.join(oscd_root, "Onera Satellite Change Detection dataset - Train Labels", city, "cm", f"{city}-cm.tif")
    has_gt = os.path.exists(gt_path)
    gt_mask = None
    if has_gt:
        with rasterio.open(gt_path) as src:
            # OSCD GT: 1=no change, 2=change
            gt_data = src.read(1)
            # Align if shape mismatch
            if gt_data.shape != (H, W):
                print(f"  [Warning] GT shape {gt_data.shape} differs from Image shape {(H, W)}. Resizing GT.")
                gt_data = cv2.resize(gt_data, (W, H), interpolation=cv2.INTER_NEAREST)
            gt_mask = (gt_data == 2).astype(np.uint8)
        print("  Ground Truth: Loaded")
    else:
        print("  Ground Truth: Not found")

    print("\nSTEP 4: Sliding Window Inference")
    tile_size = 256
    stride = 128
    
    full_prob_map = np.zeros((H, W), dtype=np.float32)
    weight_map = np.zeros((H, W), dtype=np.float32)
    
    # Track metrics to show progress
    tiles_processed = 0
    
    with torch.inference_mode():
        for y in range(0, H, stride):
            for x in range(0, W, stride):
                y_end = min(y + tile_size, H)
                x_end = min(x + tile_size, W)
                
                # Extract patch
                patch_a = img_a[:, y:y_end, x:x_end]
                patch_b = img_b[:, y:y_end, x:x_end]
                
                h_p, w_p = patch_a.shape[1:]
                
                # Pad to multiple of 32 for U-Net
                pad_h = (32 - h_p % 32) % 32
                pad_w = (32 - w_p % 32) % 32
                
                if pad_h > 0 or pad_w > 0:
                    patch_a = np.pad(patch_a, ((0,0),(0,pad_h),(0,pad_w)), mode='reflect')
                    patch_b = np.pad(patch_b, ((0,0),(0,pad_h),(0,pad_w)), mode='reflect')
                
                t_a = torch.from_numpy(patch_a).unsqueeze(0).to(device)
                t_b = torch.from_numpy(patch_b).unsqueeze(0).to(device)
                
                logits = model(t_a, t_b)
                probs = torch.sigmoid(logits).squeeze().cpu().numpy()
                
                # Crop back
                probs = probs[:h_p, :w_p]
                
                # Add to full map
                full_prob_map[y:y_end, x:x_end] += probs
                weight_map[y:y_end, x:x_end] += 1.0
                tiles_processed += 1

    # Average
    full_prob_map /= np.maximum(weight_map, 1.0)
    print(f"  Processed {tiles_processed} tiles using 256x256 window with stride {stride}")
    
    print("\nSTEP 5: Threshold Sweep & Metrics")
    thresholds = [0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
    
    from ml.inference.postprocess import postprocess_mask
    
    stats_050 = None
    
    for th in thresholds:
        b_mask, comps = postprocess_mask(full_prob_map, threshold=th)
        ch_px = int(b_mask.sum())
        ch_pct = (ch_px / b_mask.size) * 100
        
        if th == 0.50:
            stats_050 = {
                "changed_pixels": ch_px,
                "changed_pct": ch_pct,
                "regions": len(comps),
                "mask": b_mask
            }
            
        print(f"  Threshold {th:.2f}:")
        print(f"    Changed pixels: {ch_px} ({ch_pct:.2f}%)")
        print(f"    Connected regions: {len(comps)}")
        
        if has_gt:
            p, r, f1, iou = compute_metrics(b_mask, gt_mask)
            print(f"    Precision: {p:.4f} | Recall: {r:.4f} | F1: {f1:.4f} | IoU: {iou:.4f}")
            if th == 0.50:
                stats_050["metrics"] = (p, r, f1, iou)

    print("\nSTEP 6: Generate Artifacts")
    out_dir = "backend/data/inference_outputs"
    os.makedirs(out_dir, exist_ok=True)
    
    # 1. Probability Map
    prob_out = os.path.join(out_dir, f"{city}_legacy_probability_map.png")
    plt.figure(figsize=(10, 10))
    plt.imshow(full_prob_map, cmap='hot', vmin=0, vmax=1)
    plt.colorbar(label='Probability')
    plt.title(f"{city.capitalize()} - Legacy Probability Map")
    plt.tight_layout()
    plt.savefig(prob_out, dpi=150)
    plt.close()
    
    # 2. Binary Mask (at 0.5)
    mask_05 = stats_050["mask"]
    mask_out = os.path.join(out_dir, f"{city}_legacy_binary_mask.png")
    plt.figure(figsize=(10, 10))
    plt.imshow(mask_05, cmap='gray')
    plt.title(f"{city.capitalize()} - Legacy Binary Mask (Threshold=0.50)")
    plt.tight_layout()
    plt.savefig(mask_out, dpi=150)
    plt.close()
    
    # 3. Overlay (on before image)
    # img_a is (3, H, W). In legacy mode, it's roughly [0, 40] depending on brightness.
    # To display it, we just clip it and normalize to [0,1] for display purposes.
    rgb_display = np.transpose(img_a, (1, 2, 0))
    # Approximate display scaling:
    disp_max = rgb_display.max() if rgb_display.max() > 0 else 1.0
    rgb_display = np.clip(rgb_display / disp_max, 0, 1)
    
    # Make a red mask overlay
    red_overlay = np.zeros_like(rgb_display)
    red_overlay[:, :, 0] = 1.0  # pure red
    
    overlay = np.where(np.expand_dims(mask_05 > 0, axis=-1), 
                       rgb_display * 0.5 + red_overlay * 0.5, 
                       rgb_display)
                       
    overlay_out = os.path.join(out_dir, f"{city}_legacy_overlay.png")
    plt.figure(figsize=(10, 10))
    plt.imshow(overlay)
    plt.title(f"{city.capitalize()} - Legacy Change Overlay (Threshold=0.50)")
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(overlay_out, dpi=150)
    plt.close()
    
    print(f"  Saved artifacts to {out_dir}")

    # Final Report
    print("\n" + "=" * 60)
    print("FULL SCENE EVALUATION")
    print("-" * 21)
    print(f"Scene: {city.capitalize()}")
    print(f"Scene size: {W} x {H}")
    print("Model: REAL")
    print(f"Checkpoint: {os.path.basename(ckpt_path)}")
    print(f"Input channels: {in_channels}")
    print("\nProbability:")
    print(f"Min:  {full_prob_map.min():.4f}")
    print(f"Max:  {full_prob_map.max():.4f}")
    print(f"Mean: {full_prob_map.mean():.4f}")
    print("\nThreshold 0.50:")
    print(f"Changed pixels: {stats_050['changed_pixels']}")
    print(f"Changed percentage: {stats_050['changed_pct']:.2f}%")
    print(f"Connected regions: {stats_050['regions']}")
    print("\nGround Truth:")
    print(f"Available: {'YES' if has_gt else 'NO'}")
    if has_gt:
        p, r, f1, iou = stats_050["metrics"]
        print(f"Precision: {p:.4f}")
        print(f"Recall:    {r:.4f}")
        print(f"F1:        {f1:.4f}")
        print(f"IoU:       {iou:.4f}")
    print("=" * 60)

if __name__ == "__main__":
    main()
