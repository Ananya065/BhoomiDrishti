"""
smoke_test.py — Dry-run pipeline validation.
Loads 1 train city + 1 val city, performs 1 forward + backward pass,
saves a temp checkpoint, then verifies it can be re-loaded, then deletes it.
"""
import os, sys, torch
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ml.datasets.change_detection_dataset import OSCDDataset
from ml.models.model import SiameseUNetAttention
from ml.losses.focal_dice import FocalDiceLoss
from ml.evaluation.metrics import calculate_metrics
from torch.utils.data import DataLoader

DATASET_PATH = r"C:\Users\adity\OneDrive\Desktop\oscd_dataset"
SMOKE_CKPT   = os.path.join(os.path.dirname(__file__), "ml", "models", "SMOKE_TEST.pth")

def run():
    print("=== SMOKE TEST START ===")

    # --- 1. Leakage check ---
    TRAIN_CITIES = ["aguasclaras"]
    VAL_CITIES   = ["hongkong"]
    TEST_CITIES  = ["brasilia","montpellier","norcia","rio","saclay_w","valencia","dubai","lasvegas","milano","chongqing"]
    assert not set(TRAIN_CITIES) & set(VAL_CITIES),  "FAIL: train/val overlap"
    assert not set(TRAIN_CITIES) & set(TEST_CITIES), "FAIL: train/test overlap"
    assert not set(VAL_CITIES)   & set(TEST_CITIES), "FAIL: val/test overlap"
    print("✓ Leakage check passed")

    # --- 2. Dataset load ---
    train_ds = OSCDDataset(DATASET_PATH, split="train", cities=TRAIN_CITIES, patch_size=256)
    val_ds   = OSCDDataset(DATASET_PATH, split="val",   cities=VAL_CITIES,   patch_size=256)
    print(f"✓ Train patches: {len(train_ds)}  |  Val patches: {len(val_ds)}")
    assert len(train_ds) > 0, "FAIL: no training patches"
    assert len(val_ds)   > 0, "FAIL: no validation patches"

    # --- 3. DataLoader ---
    train_loader = DataLoader(train_ds, batch_size=2, shuffle=True,  num_workers=0)
    val_loader   = DataLoader(val_ds,   batch_size=2, shuffle=False, num_workers=0)

    # --- 4. Model + loss + optimizer ---
    device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model     = SiameseUNetAttention(pretrained=True, in_channels=13).to(device)
    criterion = FocalDiceLoss(alpha=0.5, beta=0.5).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", factor=0.5, patience=2, min_lr=1e-6)
    print(f"✓ Model initialized on {device}")

    # --- 5. Forward + backward ---
    model.train()
    batch = next(iter(train_loader))
    img1 = batch["img1"].to(device)
    img2 = batch["img2"].to(device)
    mask = batch["mask"].to(device)

    assert img1.shape == (img1.shape[0], 13, 256, 256), f"FAIL: wrong T1 shape {img1.shape}"
    assert img2.shape == img1.shape,                    f"FAIL: T1/T2 mismatch"
    assert mask.shape == (mask.shape[0],  1, 256, 256), f"FAIL: wrong mask shape {mask.shape}"
    print(f"✓ Input shapes — T1: {tuple(img1.shape)}, T2: {tuple(img2.shape)}, mask: {tuple(mask.shape)}")

    optimizer.zero_grad()
    outputs = model(img1, img2)
    assert outputs.shape == mask.shape, f"FAIL: output shape {outputs.shape} != mask shape {mask.shape}"
    loss = criterion(outputs, mask)
    loss.backward()
    optimizer.step()
    print(f"✓ Forward + backward pass — train loss: {loss.item():.4f}")

    # --- 6. Validation pass ---
    model.eval()
    with torch.no_grad():
        val_batch = next(iter(val_loader))
        v1 = val_batch["img1"].to(device)
        v2 = val_batch["img2"].to(device)
        vm = val_batch["mask"].to(device)
        val_out  = model(v1, v2)
        val_loss = criterion(val_out, vm)
        metrics  = calculate_metrics(val_out, vm, threshold=0.5)
    scheduler.step(val_loss.item())
    print(f"✓ Validation pass — val loss: {val_loss.item():.4f} | IoU: {metrics['iou']:.4f} | F1: {metrics['f1']:.4f}")

    # --- 7. Checkpoint save + reload ---
    torch.save({"model_state_dict": model.state_dict(), "epoch": 0, "val_loss": val_loss.item()}, SMOKE_CKPT)
    ckpt = torch.load(SMOKE_CKPT, map_location="cpu")
    model2 = SiameseUNetAttention(pretrained=False, in_channels=13)
    model2.load_state_dict(ckpt["model_state_dict"])
    print(f"✓ Checkpoint saved and reloaded from {SMOKE_CKPT}")

    os.remove(SMOKE_CKPT)
    print(f"✓ Temporary checkpoint deleted")

    print("\n=== SMOKE TEST PASSED ===")
    print("Pipeline is ready for full training.")

if __name__ == "__main__":
    run()

