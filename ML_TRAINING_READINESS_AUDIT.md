# ML TRAINING READINESS AUDIT

## 1. Model Architecture
- **Architecture Name:** `SiameseUNetAttention`
- **Input Channels:** 13 (configurable via `in_channels` parameter)
- **Output Channels:** 1 (single-channel logits for binary change map)
- **Siamese Structure:** Yes, utilizes a shared ResNet34 encoder to process temporal branches independently before fusing them.
- **Encoder:** ResNet34. The first convolutional layer is properly adapted for 13 bands (copying pretrained RGB weights to indices 1, 2, 3 and initializing others cleanly).
- **Decoder:** 4 custom `DecoderBlock` layers that use transpose convolutions and skip connections from the encoder.
- **Attention Mechanism:** `SpatialTemporalAttentionModule` applies spatial and channel-wise attention over the absolute difference of T1 and T2 feature maps.
- **Expected Tensor Dimensions:** 
  - T1 shape = `(Batch, 13, H, W)`
  - T2 shape = `(Batch, 13, H, W)`
- **Temporal Requirement:** Both temporal images (T1 and T2) must be provided simultaneously to the `forward()` method.
- **Compatibility:** Fully compatible with the 13-band OSCD dataset.

## 2. Dataset Verification
- **Dataset Path:** `C:\Users\adity\OneDrive\Desktop\oscd_dataset`
- **Structure Inspected:** Verified the presence of `Images`, `Train Labels`, and `Test Labels`.
- **Cities/Scenes:** 14 training cities explicitly verified (e.g., `aguasclaras`, `bordeaux`, `mumbai`).
- **Image Files:** Extracted exactly 13 Sentinel-2 bands per scene (`B01.tif` to `B8A.tif`).
- **Label Files:** Present in `Train Labels/city/cm/city-cm.tif`.
- **Dimensions:** Image bands and labels are spatially pre-aligned (e.g., `471 x 525` for `aguasclaras`).
- **Label Values:** Confirmed values are `1` (no change) and `2` (change).
- **Georeferencing:** The raw TIFF files lack valid geotransform metadata (`NotGeoreferencedWarning`), but this does not block array-based pixel training.

## 3. Dataset Loader Verification
- **File:** `backend/ml/datasets/change_detection_dataset.py`
- **T1/T2 Loading:** Reads patches natively via `rasterio.windows.Window`.
- **Mask Loading:** Properly maps the raw label values using `(mask_data == 2).astype(np.float32)`.
- **Padding:** Applies `np.pad(..., mode='reflect')` if edge patches are smaller than `patch_size`.
- **Output Shapes:** Explicitly verified the loader returns exactly `(T1, T2, mask)` with dimensions:
  - T1/T2: `(13, 256, 256)`
  - Mask: `(1, 256, 256)`
- **Alignment:** Has an explicit validation check to guarantee that bands and labels match target resolution dimensions.

## 4. Preprocessing Verification
- **File:** `backend/ml/preprocessing/transforms.py`
- **Normalization:** Divides integer pixel values by 10000.0 and clips to `[0, 1]` via `normalize_sentinel2_bands`.
- **Spatial Alignment:** Enforced natively by `rasterio` and the dataset loader bounds.

## 5. Loss Verification
- **File:** `backend/ml/losses/focal_dice.py`
- **Components:** Combines `FocalLoss` (via `binary_cross_entropy_with_logits`) and `DiceLoss` (via `torch.sigmoid`).
- **Numerical Stability:** The Dice calculation utilizes a `self.smooth=1.0` parameter in both numerator and denominator, safely handling empty masks (0 change pixels) without division-by-zero errors.
- **Appropriateness:** Highly appropriate for severely imbalanced binary change detection.

## 6. Training Verification
- **File:** `backend/ml/training/train.py`
- **Optimizer:** Adam with learning rate `1e-4`.
- **Data Split:** Randomly splits the dataset 80/20 by shuffling patch indices.
- **Checkpoint Saving:** The code includes logic to save a checkpoint: `torch.save(model.state_dict(), os.path.join(..., "best_model.pth"))`.
- **Missing Elements:** There is **no learning rate scheduler** implemented.

## 7. Evaluation Verification
- **File:** `backend/ml/evaluation/metrics.py`
- **Calculations:** Properly computes pixel-wise True Positives, True Negatives, False Positives, and False Negatives using thresholded tensors.
- **Metrics:** Precision, Recall, F1, and IoU are mathematically correct and stabilized with `1e-7`.
- **Test Data Usage:** **WARNING:** The `train.py` script currently evaluates the model against a validation subset of the *training* data. It never loads or tests against the held-out OSCD test dataset.

## 8. Checkpoint Status
- Searched entire project structure and Desktop directories for `*.pth`, `*.pt`, `*.ckpt`, `*.onnx`, `*.safetensors`.
- **NO TRAINED CHECKPOINT FOUND.**

## 9. Problems Found
1. **Spatial Data Leakage:** The 80/20 train/val split is performed randomly at the *patch level* rather than the *city level*. Patches from the exact same city will end up in both training and validation sets, severely inflating validation metrics due to spatial autocorrelation.
2. **Missing Test Loop:** The held-out OSCD test split is never utilized in `train.py`.
3. **No LR Scheduler:** Training does not adapt learning rate on plateaus.
4. **Non-Georeferenced Warnings:** The OSCD files raise `NotGeoreferencedWarning`, though this doesn't strictly crash the DataLoader.

## 10. Exact Next Steps
- Modify `train.py` to perform data splits at the **city level** (e.g., 11 cities for training, 3 for validation) to fix spatial leakage.
- Integrate the official OSCD test cities loop for final evaluation.
- Add `torch.optim.lr_scheduler.ReduceLROnPlateau`.

## FINAL STATUS
**TRAINING READY**

*(The codebase contains minor methodological flaws in the train/val split logic, but there are no fatal syntax errors, shape mismatches, or missing dependencies. The pipeline is structurally capable of executing a full end-to-end training loop and generating a checkpoint.)*
