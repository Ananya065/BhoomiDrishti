import os
import sys

# Ensure backend root is in sys.path so we can import from ml
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ml.utils.visualize import convert_oscd_scene_to_png

def generate_demo_imagery():
    base_dataset_path = os.environ.get("OSCD_DATASET_ROOT", r"C:\Users\adity\OneDrive\Desktop\oscd_dataset")
    cities = ["abudhabi", "beirut", "bordeaux"]
    
    media_dir = os.path.join(os.path.dirname(__file__), "media", "cases")
    os.makedirs(media_dir, exist_ok=True)
    
    for i, city in enumerate(cities, start=1):
        city_path = os.path.join(base_dataset_path, "Onera Satellite Change Detection dataset - Images", city)
        before_scene = os.path.join(city_path, "imgs_1_rect")
        after_scene = os.path.join(city_path, "imgs_2_rect")
        
        before_out = os.path.join(media_dir, f"case_demo_{i:02d}_before.png")
        after_out = os.path.join(media_dir, f"case_demo_{i:02d}_after.png")
        
        if os.path.exists(before_scene) and os.path.exists(after_scene):
            print(f"Generating for {city}...")
            convert_oscd_scene_to_png(before_scene, before_out)
            convert_oscd_scene_to_png(after_scene, after_out)
            print(f"Saved {before_out} and {after_out}")
        else:
            print(f"Warning: Missing OSCD data for {city}")

if __name__ == "__main__":
    generate_demo_imagery()
