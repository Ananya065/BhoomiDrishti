import unittest
import torch
import numpy as np
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from ml.models.model import SiameseUNetAttention
from ml.losses.focal_dice import FocalDiceLoss
from ml.evaluation.metrics import calculate_metrics
from ml.inference.postprocess import postprocess_mask

class TestMLComponents(unittest.TestCase):
    def test_model_forward(self):
        model = SiameseUNetAttention(pretrained=False, in_channels=13)
        img_a = torch.randn(2, 13, 256, 256)
        img_b = torch.randn(2, 13, 256, 256)
        
        with torch.no_grad():
            out = model(img_a, img_b)
            
        self.assertEqual(out.shape, (2, 1, 256, 256))

    def test_padding_cropping(self):
        # Simulate an image of size 799x785
        h, w = 799, 785
        pad_h = (32 - (h % 32)) % 32
        pad_w = (32 - (w % 32)) % 32
        
        self.assertEqual(pad_h, 1) # 800
        self.assertEqual(pad_w, 15) # 800
        
        padded_h = h + pad_h
        padded_w = w + pad_w
        
        self.assertTrue(padded_h % 32 == 0)
        self.assertTrue(padded_w % 32 == 0)
        
        # Simulate cropping
        prob_map = np.zeros((padded_h, padded_w))
        cropped = prob_map[:h, :w]
        
        self.assertEqual(cropped.shape, (799, 785))

    def test_postprocess_confidence(self):
        # Create a mock probability map
        prob_map = np.zeros((100, 100))
        # Create a region with high confidence
        prob_map[10:30, 10:30] = 0.95
        # Create a region with lower confidence
        prob_map[60:80, 60:80] = 0.65
        
        mask, components = postprocess_mask(prob_map, threshold=0.5, min_area=5)
        
        self.assertEqual(len(components), 2)
        
        # Check confidences are correctly calculated
        confs = [c["confidence"] for c in components]
        self.assertAlmostEqual(max(confs), 0.95, places=2)
        self.assertAlmostEqual(min(confs), 0.65, places=2)

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
