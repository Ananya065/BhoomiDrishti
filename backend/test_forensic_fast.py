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

    # Load just ONE city, ONE patch
    val_ds = OSCDDataset(dataset_path, split="val", cities=["beirut"], patch_size=256)
    
    # We will test different channel slices
    slices_to_test = {
        "First 3 (B01, B02, B03)": [0, 1, 2],
        "BGR (B02, B03, B04)": [1, 2, 3],
        "RGB (B04, B03, B02)": [3, 2, 1],
    }
    
    # Just take the first batch
    from torch.utils.data import DataLoader
    val_loader = DataLoader(val_ds, batch_size=4, shuffle=True)
    batch = next(iter(val_loader))
    
    # Force a positive mask if possible (try a few batches until mask has 1s)
    for b in val_loader:
        if b["mask"].sum() > 100:
            batch = b
            break
            
    print(f"\nFound batch with mask sum: {batch['mask'].sum().item()} pixels")
    
    for name, channels in slices_to_test.items():
        print(f"\nTesting combination: {name} (Indices: {channels})")
        
        with torch.no_grad():
            img1_base = batch["img1"][:, channels, :, :].to(device)
            img2_base = batch["img2"][:, channels, :, :].to(device)
            mask = batch["mask"].to(device)
            
            for scale_name, multiplier in [("Standard [0,1]", 1.0), ("Div by 255", 10000.0/255.0), ("No scaling [0,10000]", 10000.0), ("Mul by 2", 2.0), ("Mul by 5", 5.0)]:
                img1 = img1_base * multiplier
                img2 = img2_base * multiplier
                
                outputs = model(img1, img2)
                probs = torch.sigmoid(outputs)
                max_prob = probs.max().item()
                mean_prob = probs.mean().item()
                m = calculate_metrics(outputs, mask, threshold=0.5)
                
                print(f"  {scale_name:25s} | MaxProb: {max_prob:.4f} | MeanProb: {mean_prob:.4f} | F1: {m['f1']:.4f}")

if __name__ == "__main__":
    main()
