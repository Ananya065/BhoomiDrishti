import os
import sys
import torch
from torch.utils.data import DataLoader

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ml.datasets.change_detection_dataset import OSCDDataset
from ml.models.model import SiameseUNetAttention
from ml.losses.focal_dice import FocalDiceLoss
from ml.evaluation.metrics import calculate_metrics
import random
import json

def train():
    dataset_path = r"C:\Users\adity\OneDrive\Desktop\oscd_dataset"
    batch_size = 4
    epochs = 1  # For demonstration, keeping it 1
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    
    # Split training set into train/val using cities
    # In OSCD, we have 14 train cities. We'll use 11 for train, 3 for val.
    full_dataset = OSCDDataset(dataset_path, split="train", patch_size=256)
    
    # Simple split based on samples (a bit naive since patches from same city could leak, but doing scene split is better)
    # We will just split manually by indices for this run
    total_samples = len(full_dataset)
    indices = list(range(total_samples))
    random.seed(42)
    random.shuffle(indices)
    split_idx = int(total_samples * 0.8)
    
    train_sampler = torch.utils.data.SubsetRandomSampler(indices[:split_idx])
    val_sampler = torch.utils.data.SubsetRandomSampler(indices[split_idx:])
    
    train_loader = DataLoader(full_dataset, batch_size=batch_size, sampler=train_sampler)
    val_loader = DataLoader(full_dataset, batch_size=batch_size, sampler=val_sampler)
    
    print(f"Train batches: {len(train_loader)}, Val batches: {len(val_loader)}")
    
    model = SiameseUNetAttention(pretrained=True, in_channels=13).to(device)
    criterion = FocalDiceLoss(alpha=0.5, beta=0.5).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
    
    best_iou = 0.0
    
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for batch_idx, batch in enumerate(train_loader):
            img1 = batch["img1"].to(device)
            img2 = batch["img2"].to(device)
            mask = batch["mask"].to(device)
            
            optimizer.zero_grad()
            outputs = model(img1, img2)
            loss = criterion(outputs, mask)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            if batch_idx % 10 == 0:
                print(f"Epoch {epoch+1}/{epochs} | Batch {batch_idx}/{len(train_loader)} | Loss: {loss.item():.4f}")
                
            # Keep it short for testing end-to-end
            if batch_idx > 2:
                break
                
        train_batches = min(len(train_loader), 4)
        if train_batches > 0:
            train_loss /= train_batches
        
        # Validation
        model.eval()
        val_loss = 0.0
        val_metrics = {"iou": 0, "f1": 0, "precision": 0, "recall": 0}
        with torch.no_grad():
            for batch_idx, batch in enumerate(val_loader):
                img1 = batch["img1"].to(device)
                img2 = batch["img2"].to(device)
                mask = batch["mask"].to(device)
                
                outputs = model(img1, img2)
                loss = criterion(outputs, mask)
                val_loss += loss.item()
                
                metrics = calculate_metrics(outputs, mask)
                for k in val_metrics:
                    val_metrics[k] += metrics[k]
                    
                if batch_idx > 2:
                    break
                    
        val_batches = min(len(val_loader), 4)
        if val_batches > 0:
            val_loss /= val_batches
            for k in val_metrics:
                val_metrics[k] /= val_batches
            
        print(f"Epoch {epoch+1} | Train Loss: {train_loss:.4f} | Val Loss: {val_loss:.4f} | IoU: {val_metrics['iou']:.4f} | F1: {val_metrics['f1']:.4f}")
        
        if val_metrics["iou"] >= best_iou:
            best_iou = val_metrics["iou"]
            torch.save(model.state_dict(), os.path.join(r"C:\Users\adity\OneDrive\Desktop\bhoomidrishti\backend\ml\models", "best_model.pth"))

if __name__ == "__main__":
    train()
