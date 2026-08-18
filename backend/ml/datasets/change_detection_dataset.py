import os
import glob
import torch
from torch.utils.data import Dataset
import rasterio
import numpy as np

class OSCDDataset(Dataset):
    def __init__(self, base_path, split="train", transform=None, patch_size=256):
        self.base_path = base_path
        self.split = split
        self.transform = transform
        self.patch_size = patch_size
        
        self.images_dir = os.path.join(base_path, "Onera Satellite Change Detection dataset - Images")
        self.labels_dir = os.path.join(base_path, f"Onera Satellite Change Detection dataset - {'Train' if split == 'train' else 'Test'} Labels")
        
        split_file = os.path.join(self.images_dir, f"{split}.txt")
        self.cities = []
        if os.path.exists(split_file):
            with open(split_file, "r") as f:
                content = f.read().strip()
                self.cities = [c.strip() for c in content.split(",") if c.strip()]
        else:
            raise FileNotFoundError(f"Split file not found: {split_file}")
            
        self.samples = []
        # Precompute valid patches
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
        
        for city in self.cities:
            city_path = os.path.join(self.images_dir, city)
            imgs_1_dir = os.path.join(city_path, "imgs_1_rect")
            imgs_2_dir = os.path.join(city_path, "imgs_2_rect")
            
            lbl_path = os.path.join(self.labels_dir, city, "cm", f"{city}-cm.tif")
            if split == "train" and not os.path.exists(lbl_path):
                continue
                
            # Use B04 (10m band) to determine spatial grid
            b04_path = os.path.join(imgs_1_dir, "B04.tif")
            if not os.path.exists(b04_path):
                b04_path = os.path.join(imgs_1_dir, "B01.tif")
                
            with rasterio.open(b04_path) as src:
                w, h = src.width, src.height
                
            stride = patch_size // 2 if split == "train" else patch_size
            for y in range(0, max(1, h - patch_size + 1), stride):
                for x in range(0, max(1, w - patch_size + 1), stride):
                    self.samples.append({
                        "city": city,
                        "x": x,
                        "y": y,
                        "imgs_1_dir": imgs_1_dir,
                        "imgs_2_dir": imgs_2_dir,
                        "lbl_path": lbl_path if os.path.exists(lbl_path) else None,
                        "target_w": w,
                        "target_h": h
                    })
                    
    def __len__(self):
        return len(self.samples)
        
    def _read_bands(self, directory, x, y, target_w, target_h):
        # We read the patch. If bands are natively different size, 
        # we would resample, but OSCD provides them spatially aligned.
        # We will add an assertion to guarantee spatial alignment!
        band_names = ["B01.tif", "B02.tif", "B03.tif", "B04.tif", "B05.tif", "B06.tif", 
                      "B07.tif", "B08.tif", "B8A.tif", "B09.tif", "B10.tif", "B11.tif", "B12.tif"]
        bands = []
        
        # Calculate actual window taking into account image bounds
        actual_w = min(self.patch_size, target_w - x)
        actual_h = min(self.patch_size, target_h - y)
        window = rasterio.windows.Window(x, y, actual_w, actual_h)
        
        for b in band_names:
            path = os.path.join(directory, b)
            with rasterio.open(path) as src:
                # Part 1.1: Verify spatial alignment is maintained (OSCD dataset is pre-aligned)
                if src.width != target_w or src.height != target_h:
                    # If not aligned, we would need full-image resampling before patching.
                    # Since OSCD is already aligned, this assertion acts as a safety guard.
                    raise ValueError(f"Band {b} in {directory} is not aligned to target grid ({target_w}x{target_h}). Found {src.width}x{src.height}")
                    
                data = src.read(1, window=window)
                bands.append(data)
        
        image = np.stack(bands, axis=0).astype(np.float32)
        
        # Pad if the image patch is on the edge and smaller than patch_size
        if image.shape[1] < self.patch_size or image.shape[2] < self.patch_size:
            pad_h = self.patch_size - image.shape[1]
            pad_w = self.patch_size - image.shape[2]
            image = np.pad(image, ((0,0), (0, pad_h), (0, pad_w)), mode='reflect')
            
        # Use authoritative normalization
        from ml.preprocessing.transforms import normalize_sentinel2_bands
        return normalize_sentinel2_bands(image)
        
    def __getitem__(self, idx):
        sample = self.samples[idx]
        x, y = sample["x"], sample["y"]
        target_w, target_h = sample["target_w"], sample["target_h"]
        
        img1 = self._read_bands(sample["imgs_1_dir"], x, y, target_w, target_h)
        img2 = self._read_bands(sample["imgs_2_dir"], x, y, target_w, target_h)
        
        if sample["lbl_path"]:
            actual_w = min(self.patch_size, target_w - x)
            actual_h = min(self.patch_size, target_h - y)
            window = rasterio.windows.Window(x, y, actual_w, actual_h)
            
            with rasterio.open(sample["lbl_path"]) as src:
                # Nearest neighbor for label alignment if sizes differed, but we assert they match
                if src.width != target_w or src.height != target_h:
                    raise ValueError(f"Label {sample['lbl_path']} is not aligned to target grid ({target_w}x{target_h}). Found {src.width}x{src.height}")
                mask_data = src.read(1, window=window)
                
                # Pad label if on edge
                if mask_data.shape[0] < self.patch_size or mask_data.shape[1] < self.patch_size:
                    pad_h = self.patch_size - mask_data.shape[0]
                    pad_w = self.patch_size - mask_data.shape[1]
                    mask_data = np.pad(mask_data, ((0, pad_h), (0, pad_w)), mode='reflect')
                    
                mask = (mask_data == 2).astype(np.float32)
                mask = np.expand_dims(mask, axis=0) # (1, H, W)
        else:
            mask = np.zeros((1, self.patch_size, self.patch_size), dtype=np.float32)
            
        return {"img1": torch.from_numpy(img1), "img2": torch.from_numpy(img2), "mask": torch.from_numpy(mask)}
