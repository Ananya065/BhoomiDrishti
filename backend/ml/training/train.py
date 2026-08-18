"""
train.py — Fixed Training Pipeline for SiameseUNetAttention
============================================================
Fixes applied vs original:
  1. City-level train/validation split (no patch leakage between cities).
  2. Official OSCD test cities are NEVER used during training or validation.
  3. ReduceLROnPlateau scheduler monitors validation loss.
  4. Rich checkpoint stored with reproducibility metadata.
  5. Full per-epoch validation metrics (precision, recall, F1, IoU, accuracy).

OFFICIAL OSCD SPLITS (from dataset txt files):
  TRAIN cities (14 total):
    aguasclaras, bercy, bordeaux, nantes, paris, rennes, saclay_e,
    abudhabi, cupertino, pisa, beihai, hongkong, beirut, mumbai

  TEST cities (10 total — NEVER touched during training):
    brasilia, montpellier, norcia, rio, saclay_w,
    valencia, dubai, lasvegas, milano, chongqing

CITY-LEVEL TRAIN / VALIDATION SPLIT (deterministic, documented):
  TRAIN_CITIES (11):
    aguasclaras, bercy, bordeaux, nantes, paris, rennes, saclay_e,
    abudhabi, cupertino, pisa, beihai

  VAL_CITIES (3):
    hongkong, beirut, mumbai

  Rationale: last 3 cities from the official train.txt kept for validation.
  The split is fixed and not shuffled — it is always the same 11/3 partition.
"""

import os
import sys
import torch
import random
import json
import numpy as np
from datetime import datetime
from torch.utils.data import DataLoader

# Allow imports from the backend root
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ml.datasets.change_detection_dataset import OSCDDataset
from ml.models.model import SiameseUNetAttention
from ml.losses.focal_dice import FocalDiceLoss
from ml.evaluation.metrics import calculate_metrics

# ===========================================================
# REPRODUCIBILITY SEEDS
# ===========================================================
SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)
torch.cuda.manual_seed_all(SEED)
torch.backends.cudnn.deterministic = True
torch.backends.cudnn.benchmark = False

# ===========================================================
# CITY-LEVEL SPLITS  (never changes between runs)
# ===========================================================
# Official train cities from train.txt:
#   aguasclaras,bercy,bordeaux,nantes,paris,rennes,saclay_e,
#   abudhabi,cupertino,pisa,beihai,hongkong,beirut,mumbai
# We hold out the last 3 (hongkong, beirut, mumbai) for validation.

TRAIN_CITIES = [
    "aguasclaras", "bercy", "bordeaux", "nantes", "paris",
    "rennes", "saclay_e", "abudhabi", "cupertino", "pisa", "beihai"
]

VAL_CITIES = [
    "hongkong", "beirut", "mumbai"
]

# Official OSCD test cities (from test.txt) — NEVER used here
TEST_CITIES = [
    "brasilia", "montpellier", "norcia", "rio", "saclay_w",
    "valencia", "dubai", "lasvegas", "milano", "chongqing"
]

# ===========================================================
# LEAKAGE VERIFICATION
# ===========================================================
def verify_no_leakage():
    train_set = set(TRAIN_CITIES)
    val_set   = set(VAL_CITIES)
    test_set  = set(TEST_CITIES)

    assert train_set & val_set  == set(), f"LEAK: train ∩ val = {train_set & val_set}"
    assert train_set & test_set == set(), f"LEAK: train ∩ test = {train_set & test_set}"
    assert val_set  & test_set  == set(), f"LEAK: val ∩ test = {val_set & test_set}"
    print("✓ Leakage check PASSED — no city appears in more than one split.")

# ===========================================================
# CONFIGURATION
# ===========================================================
CONFIG = {
    "dataset_path":    r"C:\Users\adity\OneDrive\Desktop\oscd_dataset",
    "checkpoint_path": os.path.join(os.path.dirname(__file__), "..", "models", "best_model.pth"),
    "patch_size":      256,
    "batch_size":      4,
    "num_workers":     0,          # set >0 only if your OS supports multiprocessing with rasterio
    "in_channels":     13,
    "epochs":          50,
    "lr":              1e-4,
    "lr_scheduler": {
        "factor":   0.5,
        "patience": 5,
        "min_lr":   1e-6,
    },
    "loss_alpha":      0.5,        # weight of focal loss
    "loss_beta":       0.5,        # weight of dice loss
    "threshold":       0.5,
    "seed":            SEED,
    "train_cities":    TRAIN_CITIES,
    "val_cities":      VAL_CITIES,
    "test_cities":     TEST_CITIES,
}


def train():
    verify_no_leakage()

    dataset_path    = CONFIG["dataset_path"]
    patch_size      = CONFIG["patch_size"]
    batch_size      = CONFIG["batch_size"]
    num_workers     = CONFIG["num_workers"]
    epochs          = CONFIG["epochs"]
    checkpoint_path = os.path.abspath(CONFIG["checkpoint_path"])

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")
    print(f"\nTRAIN CITIES ({len(TRAIN_CITIES)}): {TRAIN_CITIES}")
    print(f"VAL   CITIES ({len(VAL_CITIES)}):   {VAL_CITIES}")
    print(f"TEST  CITIES ({len(TEST_CITIES)}):  {TEST_CITIES}")
    print()

    # ---- Datasets (city-level, patches generated AFTER city split) ----
    train_ds = OSCDDataset(dataset_path, split="train", cities=TRAIN_CITIES, patch_size=patch_size)
    val_ds   = OSCDDataset(dataset_path, split="val",   cities=VAL_CITIES,   patch_size=patch_size)

    print(f"Train patches: {len(train_ds)}  |  Val patches: {len(val_ds)}")

    train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True,  num_workers=num_workers, pin_memory=(device.type=="cuda"))
    val_loader   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False, num_workers=num_workers, pin_memory=(device.type=="cuda"))

    # ---- Model, loss, optimizer ----
    model     = SiameseUNetAttention(pretrained=True, in_channels=CONFIG["in_channels"]).to(device)
    criterion = FocalDiceLoss(alpha=CONFIG["loss_alpha"], beta=CONFIG["loss_beta"]).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=CONFIG["lr"])
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer,
        mode="min",
        factor=CONFIG["lr_scheduler"]["factor"],
        patience=CONFIG["lr_scheduler"]["patience"],
        min_lr=CONFIG["lr_scheduler"]["min_lr"],
    )

    best_val_loss = float("inf")
    best_epoch    = -1

    for epoch in range(1, epochs + 1):
        # ---- TRAIN ----
        model.train()
        train_loss = 0.0
        for batch in train_loader:
            img1 = batch["img1"].to(device)
            img2 = batch["img2"].to(device)
            mask = batch["mask"].to(device)

            optimizer.zero_grad()
            outputs = model(img1, img2)
            loss = criterion(outputs, mask)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        train_loss /= len(train_loader)

        # ---- VALIDATE ----
        model.eval()
        val_loss = 0.0
        agg = {"iou": 0, "f1": 0, "precision": 0, "recall": 0, "tp": 0, "fp": 0, "fn": 0, "tn": 0}
        with torch.no_grad():
            for batch in val_loader:
                img1 = batch["img1"].to(device)
                img2 = batch["img2"].to(device)
                mask = batch["mask"].to(device)

                outputs = model(img1, img2)
                val_loss += criterion(outputs, mask).item()
                m = calculate_metrics(outputs, mask, threshold=CONFIG["threshold"])
                for k in agg:
                    agg[k] += m[k]

        val_loss /= len(val_loader)
        n = len(val_loader)
        val_metrics = {k: agg[k] / n for k in ["iou", "f1", "precision", "recall"]}
        
        total_px = agg["tp"] + agg["fp"] + agg["fn"] + agg["tn"]
        val_metrics["accuracy"] = (agg["tp"] + agg["tn"]) / (total_px + 1e-7)

        scheduler.step(val_loss)
        current_lr = optimizer.param_groups[0]["lr"]

        print(
            f"Epoch {epoch:03d}/{epochs} | "
            f"Train Loss: {train_loss:.4f} | "
            f"Val Loss: {val_loss:.4f} | "
            f"IoU: {val_metrics['iou']:.4f} | "
            f"F1: {val_metrics['f1']:.4f} | "
            f"Prec: {val_metrics['precision']:.4f} | "
            f"Rec: {val_metrics['recall']:.4f} | "
            f"LR: {current_lr:.2e}"
        )

        # ---- CHECKPOINT (best val loss) ----
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch    = epoch
            torch.save(
                {
                    "model_state_dict": model.state_dict(),
                    "epoch":            epoch,
                    "val_loss":         val_loss,
                    "val_f1":           val_metrics["f1"],
                    "val_iou":          val_metrics["iou"],
                    "val_precision":    val_metrics["precision"],
                    "val_recall":       val_metrics["recall"],
                    "val_accuracy":     val_metrics["accuracy"],
                    "config":           CONFIG,
                    "timestamp":        datetime.utcnow().isoformat(),
                },
                checkpoint_path,
            )
            print(f"  → Checkpoint saved (epoch {epoch}, val_loss={val_loss:.4f})")

    print(f"\nTraining complete. Best epoch: {best_epoch}, best val loss: {best_val_loss:.4f}")
    print(f"Checkpoint: {checkpoint_path}")


if __name__ == "__main__":
    train()
