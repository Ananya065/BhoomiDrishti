import os
import glob
import rasterio
import json
import numpy as np

def inspect_dataset(base_path):
    print(f"Inspecting Dataset at: {base_path}")
    
    images_dir = os.path.join(base_path, "Onera Satellite Change Detection dataset - Images")
    train_labels_dir = os.path.join(base_path, "Onera Satellite Change Detection dataset - Train Labels")
    test_labels_dir = os.path.join(base_path, "Onera Satellite Change Detection dataset - Test Labels")
    
    if not os.path.exists(images_dir):
        print("Images directory not found.")
        return
        
    cities = [d for d in os.listdir(images_dir) if os.path.isdir(os.path.join(images_dir, d))]
    print(f"Total Cities: {len(cities)}")
    
    report = {
        "cities": len(cities),
        "details": {}
    }
    
    train_cities_file = os.path.join(images_dir, "train.txt")
    test_cities_file = os.path.join(images_dir, "test.txt")
    
    train_cities = []
    test_cities = []
    
    if os.path.exists(train_cities_file):
        with open(train_cities_file, "r") as f:
            train_cities = [line.strip() for line in f.readlines() if line.strip()]
    if os.path.exists(test_cities_file):
        with open(test_cities_file, "r") as f:
            test_cities = [line.strip() for line in f.readlines() if line.strip()]
            
    print(f"Train splits found: {len(train_cities)}")
    print(f"Test splits found: {len(test_cities)}")
    
    for city in cities:
        city_path = os.path.join(images_dir, city)
        imgs_1 = os.path.join(city_path, "imgs_1_rect")
        imgs_2 = os.path.join(city_path, "imgs_2_rect")
        
        bands_1 = glob.glob(os.path.join(imgs_1, "*.tif"))
        bands_2 = glob.glob(os.path.join(imgs_2, "*.tif"))
        
        has_train_label = os.path.exists(os.path.join(train_labels_dir, city, "cm", f"{city}-cm.tif"))
        
        info = {
            "bands_1": len(bands_1),
            "bands_2": len(bands_2),
            "has_train_label": has_train_label
        }
        
        if bands_1:
            with rasterio.open(bands_1[0]) as src:
                info["width"] = src.width
                info["height"] = src.height
                info["crs"] = str(src.crs)
                info["transform"] = str(src.transform)
                info["dtype"] = src.dtypes[0]
                
        if has_train_label:
            lbl_path = os.path.join(train_labels_dir, city, "cm", f"{city}-cm.tif")
            with rasterio.open(lbl_path) as src:
                info["label_width"] = src.width
                info["label_height"] = src.height
                info["label_crs"] = str(src.crs)
                mask = src.read(1)
                info["label_values"] = np.unique(mask).tolist()
                
        report["details"][city] = info
        
    print(json.dumps(report, indent=2))
    
if __name__ == "__main__":
    dataset_path = r"C:\Users\adity\OneDrive\Desktop\oscd_dataset"
    inspect_dataset(dataset_path)
