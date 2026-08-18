import torch
import random

class RandomFlip:
    def __init__(self, p=0.5):
        self.p = p

    def __call__(self, img1, img2, mask):
        if random.random() < self.p:
            img1 = torch.flip(img1, dims=[2]) # Horizontal flip
            img2 = torch.flip(img2, dims=[2])
            mask = torch.flip(mask, dims=[2])
        if random.random() < self.p:
            img1 = torch.flip(img1, dims=[1]) # Vertical flip
            img2 = torch.flip(img2, dims=[1])
            mask = torch.flip(mask, dims=[1])
        return img1, img2, mask

class ToTensor:
    def __call__(self, img1, img2, mask):
        return img1.clone().detach(), img2.clone().detach(), mask.clone().detach()
