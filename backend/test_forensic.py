import os, sys, torch
import numpy as np

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from ml.datasets.change_detection_dataset import OSCDDataset
from ml.models.model import SiameseUNetAttention
from ml.evaluation.metrics import calculate_metrics

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    ckpt_path = "ml/checkpoints/best_siamese_model.pth"
    dataset_path = os.environ.get("OSCD_DATASET_ROOT", r"C:\Users\adity\OneDrive\Desktop\oscd_dataset")
    
    ckpt = torch.load(ckpt_path, map_location="cpu", weights_only=False)
    sd = ckpt.get("model_state_dict", ckpt)
    
    in_channels = sd["initial.0.weight"].shape[1]
    print(f"Checkpoint in_channels: {in_channels}")
    print(f"Checkpoint best_f1: {ckpt.get('best_f1', 'N/A')}")
    
    model = SiameseUNetAttention(pretrained=False, in_channels=in_channels).to(device)
    model.load_state_dict(sd)
    model.eval()

    val_cities = ["hongkong", "beirut", "mumbai"]
    print(f"Original val cities: {val_cities}")
    
    # Load full 13-band validation dataset
    val_ds = OSCDDataset(dataset_path, split="val", cities=val_cities, patch_size=256)
    from torch.utils.data import DataLoader
    val_loader = DataLoader(val_ds, batch_size=4, shuffle=False)
    
    # We will test different channel slices
    # 0,1,2 = B01, B02, B03 (Coastal, Blue, Green)
    # 1,2,3 = B02, B03, B04 (Blue, Green, Red)
    # 3,2,1 = B04, B03, B02 (Red, Green, Blue) -> This is what rgb_adapter.py does
    
    slices_to_test = {
        "First 3 bands (B01, B02, B03)": [0, 1, 2],
        "BGR (B02, B03, B04)": [1, 2, 3],
        "RGB (B04, B03, B02)": [3, 2, 1],
    }
    
    agg_all = {}
    
    for name, channels in slices_to_test.items():
        print(f"\nTesting combination: {name} (Indices: {channels})")
        
        with torch.no_grad():
            for batch in val_loader:
                # Test the 3 different scalings on the chosen channels
                img1_base = batch["img1"][:, channels, :, :].to(device)
                img2_base = batch["img2"][:, channels, :, :].to(device)
                mask = batch["mask"].to(device)
                
                # The dataset ALREADY divided by 10000 and clipped to [0,1].
                # To simulate /255 (if original was [0, 10000]), we'd multiply by 10000/255.
                # To simulate no scaling (if original was [0, 10000]), we multiply by 10000.
                for scale_name, multiplier in [("Standard ([0,1])", 1.0), ("Div by 255 (approx)", 10000.0/255.0), ("No scaling (approx 10k)", 10000.0)]:
                    img1 = img1_base * multiplier
                    img2 = img2_base * multiplier
                    
                    outputs = model(img1, img2)
                    m = calculate_metrics(outputs, mask, threshold=0.5)
                    
                    key = f"{name} - {scale_name}"
                    if key not in agg_all:
                        agg_all[key] = {"iou": 0, "f1": 0, "precision": 0, "recall": 0}
                    
                    for k in ["iou", "f1", "precision", "recall"]:
                        agg_all[key][k] += m[k]
                    
        n = len(val_loader)
        for key, agg_dict in agg_all.items():
            if key.startswith(name):
                metrics = {k: agg_dict[k] / n for k in agg_dict}
                print(f"Results [{key}]: F1={metrics['f1']:.4f} | Prec={metrics['precision']:.4f} | Rec={metrics['recall']:.4f}")

if __name__ == '__main__':
    main()
