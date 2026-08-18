import torch

def calculate_metrics(preds, targets, threshold=0.5):
    """
    preds: Probability map (after sigmoid) or raw logits. If max val > 1, assumed to be logits.
    targets: Binary mask (0 or 1).
    """
    if preds.max() > 1.0 or preds.min() < 0.0:
        preds = torch.sigmoid(preds)
        
    preds = (preds > threshold).float()
    targets = targets.float()
    
    tp = (preds * targets).sum().item()
    fp = (preds * (1 - targets)).sum().item()
    fn = ((1 - preds) * targets).sum().item()
    tn = ((1 - preds) * (1 - targets)).sum().item()
    
    precision = tp / (tp + fp + 1e-7)
    recall = tp / (tp + fn + 1e-7)
    iou = tp / (tp + fp + fn + 1e-7)
    f1 = 2 * (precision * recall) / (precision + recall + 1e-7)
    
    return {
        "iou": iou,
        "f1": f1,
        "precision": precision,
        "recall": recall,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn
    }
