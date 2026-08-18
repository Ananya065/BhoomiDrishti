import os
import sys
import rasterio

def main():
    print("--- Dataset Sanity Check ---")
    oscd_root = os.environ.get("OSCD_DATASET_ROOT", r"C:\Users\adity\OneDrive\Desktop\oscd_dataset")
    if not os.path.exists(oscd_root):
        print(f"ERROR: OSCD_DATASET_ROOT {oscd_root} does not exist.")
        sys.exit(1)
        
    print(f"Using OSCD Root: {oscd_root}")
    
    images_dir = os.path.join(oscd_root, "Onera Satellite Change Detection dataset - Images")
    if not os.path.exists(images_dir):
        print(f"ERROR: Images directory not found at {images_dir}")
        sys.exit(1)
        
    train_file = os.path.join(images_dir, "train.txt")
    if os.path.exists(train_file):
        with open(train_file, "r") as f:
            cities = [c.strip() for c in f.read().split(",") if c.strip()]
        print(f"Train cities ({len(cities)}): {cities}")
    else:
        print("WARNING: train.txt not found.")
        cities = ["abudhabi"] # default test
        
    # Check spatial alignment for one city
    city = cities[0]
    city_path = os.path.join(images_dir, city, "imgs_1_rect")
    if os.path.exists(city_path):
        b04_path = os.path.join(city_path, "B04.tif")
        b01_path = os.path.join(city_path, "B01.tif")
        b10_path = os.path.join(city_path, "B10.tif")
        
        shapes = {}
        for b_name, path in [("B04 (10m)", b04_path), ("B01 (60m)", b01_path), ("B10 (60m)", b10_path)]:
            if os.path.exists(path):
                with rasterio.open(path) as src:
                    shapes[b_name] = (src.width, src.height)
                    
        print(f"Spatial Alignment Check for {city}:")
        for k, v in shapes.items():
            print(f"  {k}: {v}")
            
        all_shapes = list(shapes.values())
        if all(s == all_shapes[0] for s in all_shapes):
            print("  -> Alignment OK: Dataset is natively aligned.")
        else:
            print("  -> Alignment WARNING: Dataset bands have different shapes, resampling will be active.")
            
    print("--- Done ---")

if __name__ == "__main__":
    main()
