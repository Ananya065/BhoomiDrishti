import os
import sys
import torch

def main():
    print("--- Model Sanity Check ---")
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    sys.path.append(backend_dir)
    from ml.models.model import SiameseUNetAttention
    
    print("Initializing SiameseUNetAttention with in_channels=13...")
    model = SiameseUNetAttention(pretrained=False, in_channels=13)
    
    # Calculate parameter count
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    
    print(f"Total Parameters: {total_params:,}")
    print(f"Trainable Parameters: {trainable_params:,}")
    
    print("Running forward pass test with mock (13, 256, 256) data...")
    tensor_a = torch.randn(1, 13, 256, 256)
    tensor_b = torch.randn(1, 13, 256, 256)
    
    model.eval()
    with torch.no_grad():
        out = model(tensor_a, tensor_b)
        
    print(f"Input shape: {tensor_a.shape}")
    print(f"Output shape: {out.shape}")
    
    if out.shape == (1, 1, 256, 256):
        print("-> Forward pass successful. Spatial dimensions maintained.")
    else:
        print("-> ERROR: Output shape is incorrect.")
        sys.exit(1)
        
    checkpoint_path = os.environ.get("MODEL_CHECKPOINT_PATH", os.path.join(backend_dir, "ml", "models", "best_model.pth"))
    if os.path.exists(checkpoint_path):
        print(f"Checkpoint found at: {checkpoint_path}")
        try:
            model.load_state_dict(torch.load(checkpoint_path, map_location="cpu"))
            print("-> Checkpoint loaded successfully. Dimensions match.")
        except Exception as e:
            print(f"-> ERROR loading checkpoint: {e}")
    else:
        print(f"WARNING: No checkpoint found at {checkpoint_path}")
        
    print("--- Done ---")

if __name__ == "__main__":
    main()
