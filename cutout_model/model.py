"""A small U-Net: a 4-channel crop (RGB plus the box) in, one channel of subject logits out."""
from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


def _block(cin: int, cout: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(cin, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
        nn.Conv2d(cout, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True))


class UNet(nn.Module):
    """Five levels. Input side must be divisible by 16."""

    def __init__(self, in_channels: int = 4, widths=(32, 64, 128, 256, 512)):
        super().__init__()
        self.widths = list(widths)
        self.down = nn.ModuleList()
        cin = in_channels
        for width in widths:
            self.down.append(_block(cin, width))
            cin = width
        self.up = nn.ModuleList(_block(widths[i + 1] + widths[i], widths[i]) for i in reversed(range(len(widths) - 1)))
        self.head = nn.Conv2d(widths[0], 1, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        skips = []
        for i, block in enumerate(self.down):
            if i:
                x = F.max_pool2d(x, 2)
            x = block(x)
            skips.append(x)
        for block, skip in zip(self.up, reversed(skips[:-1])):
            x = F.interpolate(x, size=skip.shape[-2:], mode="bilinear", align_corners=False)
            x = block(torch.cat([x, skip], dim=1))
        return self.head(x)
