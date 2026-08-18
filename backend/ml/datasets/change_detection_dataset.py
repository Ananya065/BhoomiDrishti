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
        for city in self.cities:
            city_path = os.path.join(self.images_dir, city)
            imgs_1_dir = os.path.join(city_path, "imgs_1_rect")
            imgs_2_dir = os.path.join(city_path, "imgs_2_rect")
            
            # Label might not exist for test set in OSCD, but we are supposed to have it for validation if we use train/val split
            lbl_path = os.path.join(self.labels_dir, city, "cm", f"{city}-cm.tif")
            if split == "train" and not os.path.exists(lbl_path):
                continue
                
            with rasterio.open(os.path.join(imgs_1_dir, "B01.tif")) as src:
                w, h = src.width, src.height
                
            # Create overlapping patches
            stride = patch_size // 2 if split == "train" else patch_size
            for y in range(0, h - patch_size + 1, stride):
                for x in range(0, w - patch_size + 1, stride):
                    self.samples.append({
                        "city": city,
                        "x": x,
                        "y": y,
                        "imgs_1_dir": imgs_1_dir,
                        "imgs_2_dir": imgs_2_dir,
                        "lbl_path": lbl_path if os.path.exists(lbl_path) else None
                    })
                    
    def __len__(self):
        return len(self.samples)
        
    def _read_bands(self, directory, x, y):
        # Read 13 bands in fixed order to ensure consistency
        band_names = ["B01.tif", "B02.tif", "B03.tif", "B04.tif", "B05.tif", "B06.tif", 
                      "B07.tif", "B08.tif", "B8A.tif", "B09.tif", "B10.tif", "B11.tif", "B12.tif"]
        bands = []
        for b in band_names:
            path = os.path.join(directory, b)
            with rasterio.open(path) as src:
                window = rasterio.windows.Window(x, y, self.patch_size, self.patch_size)
                data = src.read(1, window=window)
                bands.append(data)
        
        # Stack to shape (13, H, W)
        image = np.stack(bands, axis=0).astype(np.float32)
        # Simple normalization: divide by 10000.0 (common for Sentinel-2)
        image = image / 10000.0
        image = np.clip(image, 0.0, 1.0)
        return image
        
    def __getitem__(self, idx):
        sample = self.samples[idx]
        x, y = sample["x"], sample["y"]
        
        img1 = self._read_bands(sample["imgs_1_dir"], x, y)
        img2 = self._read_bands(sample["imgs_2_dir"], x, y)
        
        if sample["lbl_path"]:
            with rasterio.open(sample["lbl_path"]) as src:
                window = rasterio.windows.Window(x, y, self.patch_size, self.patch_size)
                mask_data = src.read(1, window=window)
                # OSCD label values: 1 is no change, 2 is change
                mask = (mask_data == 2).astype(np.float32)
                mask = np.expand_dims(mask, axis=0) # (1, H, W)
        else:
            mask = np.zeros((1, self.patch_size, self.patch_size), dtype=np.float32)
            
        img1 = torch.from_numpy(img1)
        img2 = torch.from_numpy(img2)
        mask = torch.from_numpy(mask)
        
        if self.transform:
            # We can apply simple random flips, ensuring all 3 tensors are flipped identically
            pass
            
        return {"img1": img1, "img2": img2, "mask": mask}
