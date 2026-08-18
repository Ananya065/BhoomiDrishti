import unittest
import torch
import numpy as np
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ml.models.model import SiameseUNetAttention
from ml.losses.focal_dice import FocalDiceLoss
from ml.evaluation.metrics import calculate_metrics

class TestMLComponents(unittest.TestCase):
    def test_model_forward(self):
        model = SiameseUNetAttention(pretrained=False, in_channels=13)
        img_a = torch.randn(2, 13, 256, 256)
        img_b = torch.randn(2, 13, 256, 256)
        
        with torch.no_grad():
            out = model(img_a, img_b)
            
        self.assertEqual(out.shape, (2, 1, 256, 256))

    def test_losses(self):
        criterion = FocalDiceLoss()
        preds = torch.randn(2, 1, 64, 64)
        targets = torch.randint(0, 2, (2, 1, 64, 64)).float()
        
        loss = criterion(preds, targets)
        self.assertTrue(loss.item() > 0)
        
    def test_metrics(self):
        preds = torch.tensor([[[[0.9, 0.1], [0.8, 0.2]]]])
        targets = torch.tensor([[[[1, 0], [1, 0]]]])
        
        metrics = calculate_metrics(preds, targets, threshold=0.5)
        self.assertEqual(metrics["tp"], 2)
        self.assertEqual(metrics["fp"], 0)
        self.assertEqual(metrics["fn"], 0)
        self.assertEqual(metrics["tn"], 2)
        self.assertAlmostEqual(metrics["iou"], 1.0, places=5)
        self.assertAlmostEqual(metrics["f1"], 1.0, places=5)

if __name__ == '__main__':
    unittest.main()
