"""
evaluate_test.py — Official OSCD Test Set Evaluation
======================================================
RULES:
  - This script is run ONLY after a final trained checkpoint exists.
  - It loads ONLY the official OSCD test cities.
  - It uses identical preprocessing to training.
  - It does NOT modify any model weights.
  - It does NOT influence training, validation, or hyperparameter selection.

Usage:
    cd C:\\Users\\adity\\OneDrive\\Desktop\\bhoomidrishti\\backend
    python -m ml.evaluation.evaluate_test

Expected output:
    Per-city metrics table + aggregate metrics.
"""

import os
import sys
import torch
import numpy as np
from collections import defaultdict
from torch.utils.data import DataLoader

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ml.datasets.change_detection_dataset import OSCDDataset
from ml.models.model import SiameseUNetAttention
from ml.evaluation.metrics import calculate_metrics

# ===========================================================
# CONFIGURATION
# ===========================================================
DATASET_PATH    = r"C:\Users\adity\OneDrive\Desktop\oscd_dataset"
CHECKPOINT_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "best_model.pth")
PATCH_SIZE      = 256
BATCH_SIZE      = 4
IN_CHANNELS     = 13
THRESHOLD       = 0.5   # Must match the threshold used during training — DO NOT tune this here

# Official OSCD test cities (from test.txt) — identical to TEST_CITIES in train.py
TEST_CITIES = [
    "brasilia", "montpellier", "norcia", "rio", "saclay_w",
    "valencia", "dubai", "lasvegas", "milano", "chongqing"
]


def evaluate():
    checkpoint_path = os.path.abspath(CHECKPOINT_PATH)
    if not os.path.exists(checkpoint_path):
        print(f"ERROR: Checkpoint not found at {checkpoint_path}")
        print("Run training first:  python -m ml.training.train")
        return

    # ---- Load checkpoint ----
    print(f"Loading checkpoint: {checkpoint_path}")
    ckpt = torch.load(checkpoint_path, map_location="cpu")
    
    # Handle both raw state_dict (legacy) and rich checkpoint dict
    if "model_state_dict" in ckpt:
        state_dict = ckpt["model_state_dict"]
        saved_epoch    = ckpt.get("epoch", "unknown")
        saved_val_loss = ckpt.get("val_loss", "unknown")
        saved_val_f1   = ckpt.get("val_f1", "unknown")
        print(f"  Epoch: {saved_epoch} | Val Loss: {saved_val_loss} | Val F1: {saved_val_f1}")
    else:
        # Legacy: raw state_dict
        state_dict = ckpt
        print("  (Legacy checkpoint — raw state_dict)")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}\n")

    model = SiameseUNetAttention(pretrained=False, in_channels=IN_CHANNELS).to(device)
    model.load_state_dict(state_dict)
    model.eval()

    # ---- Build test dataset from official test cities ----
    # Test cities' labels live in "Test Labels" folder
    test_ds = OSCDDataset(
        DATASET_PATH,
        split="test",
        cities=TEST_CITIES,
        label_split="test",
        patch_size=PATCH_SIZE,
    )
    
    print(f"Test cities ({len(TEST_CITIES)}): {TEST_CITIES}")
    print(f"Total test patches: {len(test_ds)}")
    
    # Count patches per city for reporting
    city_patch_count = defaultdict(int)
    for s in test_ds.samples:
        city_patch_count[s["city"]] += 1

    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    # ---- Per-city accumulators ----
    city_agg = defaultdict(lambda: {"tp": 0.0, "fp": 0.0, "fn": 0.0, "tn": 0.0, "n": 0})

    # We need per-patch city labels — iterate with index
    patch_city_map = [s["city"] for s in test_ds.samples]
    
    global_agg = {"tp": 0.0, "fp": 0.0, "fn": 0.0, "tn": 0.0}
    total_changed   = 0.0
    total_unchanged = 0.0

    batch_start = 0
    with torch.no_grad():
        for batch in test_loader:
            img1 = batch["img1"].to(device)
            img2 = batch["img2"].to(device)
            mask = batch["mask"].to(device)

            outputs = model(img1, img2)
            m = calculate_metrics(outputs, mask, threshold=THRESHOLD)

            bs = img1.size(0)
            # Distribute pixel counts to per-city (approximate — batch may span cities)
            for k in ["tp", "fp", "fn", "tn"]:
                global_agg[k] += m[k]
            
            # Per-city: accumulate by first city in batch (approximation when batch spans cities)
            for b_idx in range(bs):
                city = patch_city_map[batch_start + b_idx]
                city_agg[city]["n"] += 1
            
            # Per-batch metrics split by city within batch
            for b_idx in range(bs):
                city = patch_city_map[batch_start + b_idx]
                single_out  = outputs[b_idx:b_idx+1]
                single_mask = mask[b_idx:b_idx+1]
                sm = calculate_metrics(single_out, single_mask, threshold=THRESHOLD)
                for k in ["tp", "fp", "fn", "tn"]:
                    city_agg[city][k] += sm[k]

            total_changed   += (mask > 0.5).float().sum().item()
            total_unchanged += (mask < 0.5).float().sum().item()
            batch_start += bs

    # ---- Per-city table ----
    print("\n" + "="*75)
    print(f"{'City':<16} {'Precision':>9} {'Recall':>9} {'F1':>9} {'IoU':>9} {'Accuracy':>9}")
    print("-"*75)
    
    city_metrics = {}
    for city in TEST_CITIES:
        a = city_agg.get(city, {"tp": 0, "fp": 0, "fn": 0, "tn": 0})
        tp, fp, fn, tn = a["tp"], a["fp"], a["fn"], a["tn"]
        prec = tp / (tp + fp + 1e-7)
        rec  = tp / (tp + fn + 1e-7)
        f1   = 2 * prec * rec / (prec + rec + 1e-7)
        iou  = tp / (tp + fp + fn + 1e-7)
        acc  = (tp + tn) / (tp + fp + fn + tn + 1e-7)
        city_metrics[city] = {"precision": prec, "recall": rec, "f1": f1, "iou": iou, "accuracy": acc}
        patches = city_patch_count.get(city, 0)
        print(f"{city:<16} {prec:>9.4f} {rec:>9.4f} {f1:>9.4f} {iou:>9.4f} {acc:>9.4f}  ({patches} patches)")
    
    # ---- Overall aggregate ----
    tp = global_agg["tp"]; fp = global_agg["fp"]
    fn = global_agg["fn"]; tn = global_agg["tn"]
    g_prec = tp / (tp + fp + 1e-7)
    g_rec  = tp / (tp + fn + 1e-7)
    g_f1   = 2 * g_prec * g_rec / (g_prec + g_rec + 1e-7)
    g_iou  = tp / (tp + fp + fn + 1e-7)
    g_acc  = (tp + tn) / (tp + fp + fn + tn + 1e-7)

    print("="*75)
    print("\nOVERALL TEST METRICS")
    print(f"  Precision:      {g_prec:.4f}")
    print(f"  Recall:         {g_rec:.4f}")
    print(f"  F1:             {g_f1:.4f}")
    print(f"  IoU:            {g_iou:.4f}")
    print(f"  Accuracy:       {g_acc:.4f}")
    print()
    print(f"  Test cities:    {len(TEST_CITIES)}")
    print(f"  Test patches:   {len(test_ds)}")
    print(f"  Changed px:     {int(total_changed)}")
    print(f"  Unchanged px:   {int(total_unchanged)}")
    print(f"  Threshold:      {THRESHOLD}")
    print(f"  Checkpoint:     {checkpoint_path}")
    print("="*75)


if __name__ == "__main__":
    evaluate()
