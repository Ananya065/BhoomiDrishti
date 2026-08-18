# ML TRAINING PIPELINE — FIXED

## 1. Original Problems
The original `train.py` contained three methodological errors:

1. **Spatial Data Leakage**: Train/validation split was performed randomly at the *patch level*. Because OSCD scenes are spatially autocorrelated, patches from the exact same city appeared in both training and validation — artificially inflating validation IoU.
2. **Missing Test Evaluation**: The official OSCD test cities were never evaluated.
3. **No LR Scheduler**: Learning rate was fixed for the entire training duration.

---

## 2. Spatial Leakage — Explanation
OSCD is a change-detection benchmark where each city contains hundreds of spatially overlapping 256×256 patches. If you shuffle *all patches from all cities* and then split 80/20, patches from city `mumbai` will appear in both the train set and the validation set — just at slightly different offsets. The model can trivially memorize local textures. This makes the validation F1/IoU appear far better than it truly is.

**Correct approach**: split at the **city level** first, then extract patches independently.

---

## 3. New City-Level Split
Split is **deterministic and fixed**. The last 3 cities from the official `train.txt` are held out as validation.

### TRAIN CITIES (11)
```
aguasclaras, bercy, bordeaux, nantes, paris, rennes, saclay_e,
abudhabi, cupertino, pisa, beihai
```

### VALIDATION CITIES (3)
```
hongkong, beirut, mumbai
```

### TEST CITIES (10) — NEVER used during training/validation
```
brasilia, montpellier, norcia, rio, saclay_w,
valencia, dubai, lasvegas, milano, chongqing
```

**Verified invariant:**
- `set(TRAIN) ∩ set(VAL) = ∅`
- `set(TRAIN) ∩ set(TEST) = ∅`
- `set(VAL) ∩ set(TEST) = ∅`

---

## 4. Preprocessing (unchanged)
| Parameter | Value |
|---|---|
| Bands | 13 Sentinel-2 bands: B01–B12 + B8A |
| Patch size | 256 × 256 px |
| Stride (train) | 128 px (50% overlap) |
| Stride (val/test) | 256 px (no overlap) |
| Normalization | divide by 10000, clip to [0, 1] |
| Change label | value=2 in cm.tif → 1.0 (changed) |
| No-change label | value=1 in cm.tif → 0.0 |
| Padding | `reflect` padding for edge patches |

---

## 5. Training Configuration
| Parameter | Value |
|---|---|
| Model | SiameseUNetAttention (ResNet34 Siamese + Attention U-Net) |
| In channels | 13 |
| Loss | FocalDiceLoss(alpha=0.5, beta=0.5) |
| Optimizer | Adam |
| Learning rate | 1e-4 |
| Epochs | 50 |
| Batch size | 4 |
| Random seed | 42 |

---

## 6. Scheduler
```
torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer,
    mode="min",         # monitors validation loss
    factor=0.5,         # halve LR on plateau
    patience=5,         # wait 5 epochs before reducing
    min_lr=1e-6,        # floor
)
```
Scheduler is stepped with `val_loss` at the end of each epoch.

---

## 7. Checkpoint Strategy
Best checkpoint saved to: `backend/ml/models/best_model.pth`

Stored as a **rich dict** for reproducibility:
```python
{
  "model_state_dict": ...,
  "epoch":            int,
  "val_loss":         float,
  "val_f1":           float,
  "val_iou":          float,
  "val_precision":    float,
  "val_recall":       float,
  "val_accuracy":     float,
  "config":           dict,    # full training config
  "timestamp":        str,     # UTC ISO timestamp
}
```
The `model_service.py` has been updated to handle both the new rich dict and any legacy raw state_dict.

---

## 8. Evaluation Methodology
- Validation runs after every epoch using ONLY the 3 validation cities.
- Metrics: Loss, Precision, Recall, F1, IoU, Accuracy (pixel-wise, threshold=0.5).
- Test evaluation is run **only once** after training is complete using `evaluate_test.py`.

---

## 9. Leakage Verification
The pipeline enforces three set-intersection checks at runtime in `verify_no_leakage()`:
```
assert set(TRAIN_CITIES) & set(VAL_CITIES)  == set()
assert set(TRAIN_CITIES) & set(TEST_CITIES) == set()
assert set(VAL_CITIES)   & set(TEST_CITIES) == set()
```
This runs before any data is loaded or any model is initialized.

---

## 10. Dry-Run Result — PASSED

```
=== SMOKE TEST START ===
OK Leakage check passed
OK Train patches: 58  |  Val patches: 33
OK Model initialized on cpu
OK Input shapes -- T1: (2, 13, 256, 256), T2: (2, 13, 256, 256), mask: (2, 1, 256, 256)
OK Forward + backward pass -- train loss: 0.5093
OK Validation pass -- val loss: 0.5023 | IoU: 0.0000 | F1: 0.0000
OK Checkpoint saved and reloaded from .../SMOKE_TEST.pth
OK Temporary checkpoint deleted

=== SMOKE TEST PASSED ===
Pipeline is ready for full training.
```

> Note: IoU=0.0000 on a 1-epoch smoke test is expected — the model has only seen one training batch and has not learned to detect change yet.

---

## 11. Files Changed
| File | Change |
|---|---|
| `backend/ml/datasets/change_detection_dataset.py` | Added `cities` and `label_split` params; city-level label folder resolution; fixed label existence guard |
| `backend/ml/training/train.py` | City-level split; ReduceLROnPlateau; rich checkpoint; full val metrics; leakage check |
| `backend/ml/evaluation/evaluate_test.py` | **[NEW]** Official test-set evaluation script with per-city table |
| `backend/ml/services/model_service.py` | Handle both rich dict and legacy state_dict checkpoint formats |
| `backend/smoke_test.py` | **[NEW]** Dry-run validation script |

---

## 12. Exact Commands

### Full Training
```powershell
cd C:\Users\adity\OneDrive\Desktop\bhoomidrishti\backend
..\backend\venv\Scripts\activate.ps1
python -m ml.training.train
```

### Test Evaluation (after training completes)
```powershell
cd C:\Users\adity\OneDrive\Desktop\bhoomidrishti\backend
..\backend\venv\Scripts\activate.ps1
python -m ml.evaluation.evaluate_test
```

### Smoke Test (before full training)
```powershell
cd C:\Users\adity\OneDrive\Desktop\bhoomidrishti\backend
..\backend\venv\Scripts\activate.ps1
python smoke_test.py
```

---

## 13. Expected Output Locations
| Artifact | Path |
|---|---|
| Trained checkpoint | `backend/ml/models/best_model.pth` |
| Test results | Printed to stdout from `evaluate_test.py` |

---

## 14. Estimated Disk Usage
| Item | Size |
|---|---|
| Model checkpoint | ~95–100 MB |
| OSCD dataset | Already on disk |
| Total overhead | ~100 MB |

---

## 15. Estimated Runtime (CPU-only)
| Phase | Estimate |
|---|---|
| Dataset loading | ~30 seconds |
| Per epoch (CPU, 11 train cities) | ~30–90 minutes |
| 50 epochs total (CPU) | ~25–75 hours |
| Per epoch (NVIDIA GPU, ~8GB VRAM) | ~2–5 minutes |
| 50 epochs (GPU) | ~2–4 hours |

> **Recommendation**: Run training on a machine with a CUDA-capable GPU. The pipeline correctly auto-detects `cuda` if available.
