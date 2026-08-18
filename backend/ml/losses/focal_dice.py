import torch
import torch.nn as nn
import torch.nn.functional as F

class FocalLoss(nn.Module):
    def __init__(self, alpha=0.25, gamma=2.0, reduction='mean'):
        super(FocalLoss, self).__init__()
        self.alpha = alpha
        self.gamma = gamma
        self.reduction = reduction

    def forward(self, inputs, targets):
        bce_loss = F.binary_cross_entropy_with_logits(inputs, targets, reduction='none')
        pt = torch.exp(-bce_loss)
        focal_loss = self.alpha * (1 - pt) ** self.gamma * bce_loss
        
        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        else:
            return focal_loss

class DiceLoss(nn.Module):
    def __init__(self, smooth=1.0):
        super(DiceLoss, self).__init__()
        self.smooth = smooth

    def forward(self, inputs, targets):
        inputs = torch.sigmoid(inputs)
        inputs = inputs.view(-1)
        targets = targets.view(-1)
        
        intersection = (inputs * targets).sum()
        dice = (2. * intersection + self.smooth) / (inputs.sum() + targets.sum() + self.smooth)
        
        return 1 - dice

class FocalDiceLoss(nn.Module):
    def __init__(self, alpha=0.5, beta=0.5, focal_alpha=0.25, focal_gamma=2.0, dice_smooth=1.0):
        super(FocalDiceLoss, self).__init__()
        self.alpha = alpha
        self.beta = beta
        self.focal = FocalLoss(alpha=focal_alpha, gamma=focal_gamma)
        self.dice = DiceLoss(smooth=dice_smooth)

    def forward(self, inputs, targets):
        focal_loss = self.focal(inputs, targets)
        dice_loss = self.dice(inputs, targets)
        return self.alpha * focal_loss + self.beta * dice_loss
