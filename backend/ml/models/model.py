import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.models as models

class SpatialTemporalAttentionModule(nn.Module):
    """
    Attention module to suppress seasonal/lighting noise and focus on structural human developments.
    Applies spatial and channel difference attention between time features.
    """
    def __init__(self, in_channels: int):
        super(SpatialTemporalAttentionModule, self).__init__()
        self.channel_attn = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Conv2d(in_channels * 2, in_channels // 2, kernel_size=1),
            nn.ReLU(inplace=True),
            nn.Conv2d(in_channels // 2, in_channels, kernel_size=1),
            nn.Sigmoid()
        )
        self.spatial_attn = nn.Sequential(
            nn.Conv2d(2, 1, kernel_size=7, padding=3),
            nn.Sigmoid()
        )

    def forward(self, feat_a: torch.Tensor, feat_b: torch.Tensor) -> torch.Tensor:
        # Absolute temporal difference
        diff = torch.abs(feat_a - feat_b)
        
        # Channel Attention
        concat_feat = torch.cat([feat_a, feat_b], dim=1)
        c_weight = self.channel_attn(concat_feat)
        diff_c = diff * c_weight
        
        # Spatial Attention
        avg_out = torch.mean(diff_c, dim=1, keepdim=True)
        max_out, _ = torch.max(diff_c, dim=1, keepdim=True)
        s_weight = self.spatial_attn(torch.cat([avg_out, max_out], dim=1))
        
        return diff_c * s_weight

class DecoderBlock(nn.Module):
    def __init__(self, in_channels: int, skip_channels: int, out_channels: int):
        super(DecoderBlock, self).__init__()
        self.up = nn.ConvTranspose2d(in_channels, in_channels // 2, kernel_size=2, stride=2)
        self.conv = nn.Sequential(
            nn.Conv2d((in_channels // 2) + skip_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(inplace=True)
        )

    def forward(self, x: torch.Tensor, skip: torch.Tensor) -> torch.Tensor:
        x = self.up(x)
        if x.shape[2:] != skip.shape[2:]:
            x = F.interpolate(x, size=skip.shape[2:], mode='bilinear', align_corners=True)
        x = torch.cat([x, skip], dim=1)
        return self.conv(x)

class SiameseUNetAttention(nn.Module):
    def __init__(self, pretrained: bool = True, in_channels: int = 3):
        super(SiameseUNetAttention, self).__init__()
        
        # Shared Encoder Backbone (ResNet34)
        resnet = models.resnet34(weights=models.ResNet34_Weights.DEFAULT if pretrained else None)
        
        # Adapt first convolutional layer if in_channels != 3
        if in_channels != 3:
            original_conv = resnet.conv1
            new_conv = nn.Conv2d(
                in_channels, 
                original_conv.out_channels, 
                kernel_size=original_conv.kernel_size, 
                stride=original_conv.stride, 
                padding=original_conv.padding, 
                bias=original_conv.bias is not None
            )
            
            if pretrained:
                # Scientifically justified band strategy:
                # For Sentinel-2, bands are [B01, B02(B), B03(G), B04(R), B05, B06, B07, B08, B09, B10, B11, B12, B8A]
                # RGB are at indices 3 (Red), 2 (Green), 1 (Blue)
                # We copy the pretrained RGB weights into these specific channels.
                # For the remaining channels, we initialize them with the mean of the pretrained RGB weights
                # divided by the number of extra channels to preserve the initial activation variance.
                with torch.no_grad():
                    # Initialize all weights with Kaiming normal
                    nn.init.kaiming_normal_(new_conv.weight, mode='fan_out', nonlinearity='relu')
                    
                    if in_channels == 13:
                        # Map Red to B04 (idx 3), Green to B03 (idx 2), Blue to B02 (idx 1)
                        # Pretrained is RGB (Red=0, Green=1, Blue=2)
                        new_conv.weight[:, 3, :, :] = original_conv.weight[:, 0, :, :] # Red
                        new_conv.weight[:, 2, :, :] = original_conv.weight[:, 1, :, :] # Green
                        new_conv.weight[:, 1, :, :] = original_conv.weight[:, 2, :, :] # Blue
                        
                        # For other channels, we scale the initialization to not blow up activations
                        # average pretrained weight power across 3 channels
                        mean_weight = original_conv.weight.mean(dim=1, keepdim=True)
                        for i in range(13):
                            if i not in [1, 2, 3]:
                                new_conv.weight[:, i:i+1, :, :] = mean_weight / 10.0 # dampening factor
                    else:
                        # Fallback for other arbitrary channel counts
                        # Repeat the 3-channel weights to fill the new channels
                        repeats = (in_channels + 2) // 3
                        repeated_weight = original_conv.weight.repeat(1, repeats, 1, 1)[:, :in_channels, :, :]
                        new_conv.weight = nn.Parameter(repeated_weight * (3.0 / in_channels))
            
            resnet.conv1 = new_conv

        self.initial = nn.Sequential(
            resnet.conv1,
            resnet.bn1,
            resnet.relu
        )
        self.maxpool = resnet.maxpool
        
        self.layer1 = resnet.layer1
        self.layer2 = resnet.layer2
        self.layer3 = resnet.layer3
        self.layer4 = resnet.layer4
        
        self.attn1 = SpatialTemporalAttentionModule(64)
        self.attn2 = SpatialTemporalAttentionModule(128)
        self.attn3 = SpatialTemporalAttentionModule(256)
        self.attn4 = SpatialTemporalAttentionModule(512)
        
        self.dec4 = DecoderBlock(512, 256, 256)
        self.dec3 = DecoderBlock(256, 128, 128)
        self.dec2 = DecoderBlock(128, 64, 64)
        self.dec1 = DecoderBlock(64, 64, 32)
        
        self.final_up = nn.ConvTranspose2d(32, 16, kernel_size=2, stride=2)
        self.final_conv = nn.Sequential(
            nn.Conv2d(16, 16, kernel_size=3, padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(inplace=True),
            nn.Conv2d(16, 1, kernel_size=1)
        )

    def extract_features(self, x: torch.Tensor):
        x0 = self.initial(x)
        x1 = self.layer1(self.maxpool(x0))
        x2 = self.layer2(x1)
        x3 = self.layer3(x2)
        x4 = self.layer4(x3)
        return x0, x1, x2, x3, x4

    def forward(self, img_a: torch.Tensor, img_b: torch.Tensor) -> torch.Tensor:
        f_a0, f_a1, f_a2, f_a3, f_a4 = self.extract_features(img_a)
        f_b0, f_b1, f_b2, f_b3, f_b4 = self.extract_features(img_b)
        
        diff1 = self.attn1(f_a1, f_b1)
        diff2 = self.attn2(f_a2, f_b2)
        diff3 = self.attn3(f_a3, f_b3)
        diff4 = self.attn4(f_a4, f_b4)
        
        d4 = self.dec4(diff4, diff3)
        d3 = self.dec3(d4, diff2)
        d2 = self.dec2(d3, diff1)
        d1 = self.dec1(d2, f_a0)
        
        out = self.final_up(d1)
        logits = self.final_conv(out)
        return logits
