"""Small U-Net baseline (Ronneberger et al. 2015 style). An implementation starting point,
not a novelty claim."""
from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F

ARCHITECTURE = "unet_small_v1"


class _Block(nn.Sequential):
    def __init__(self, cin: int, cout: int):
        super().__init__(
            nn.Conv2d(cin, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
            nn.Conv2d(cout, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
        )


class UNet(nn.Module):
    def __init__(self, in_channels: int = 3, n_classes: int = 3, base: int = 16, depth: int = 4):
        super().__init__()
        if depth < 2 or base < 4:
            raise ValueError("depth >= 2 and base >= 4 required")
        widths = [base * 2 ** i for i in range(depth)]
        self.down = nn.ModuleList()
        cin = in_channels
        for w in widths:
            self.down.append(_Block(cin, w))
            cin = w
        self.bottom = _Block(widths[-1], widths[-1] * 2)
        self.up = nn.ModuleList()
        self.dec = nn.ModuleList()
        cin = widths[-1] * 2
        for w in reversed(widths):
            self.up.append(nn.ConvTranspose2d(cin, w, 2, stride=2))
            self.dec.append(_Block(w * 2, w))
            cin = w
        self.head = nn.Conv2d(widths[0], n_classes, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        skips = []
        for block in self.down:
            x = block(x)
            skips.append(x)
            x = F.max_pool2d(x, 2)
        x = self.bottom(x)
        for up, dec, skip in zip(self.up, self.dec, reversed(skips)):
            x = dec(torch.cat([up(x), skip], dim=1))
        return self.head(x)


def build(arch: dict) -> UNet:
    if arch.get("name") != ARCHITECTURE:
        raise ValueError(f"Unsupported architecture {arch.get('name')!r}")
    return UNet(arch["in_channels"], arch["n_classes"], arch["base_channels"], arch["depth"])


def segmentation_loss(logits: torch.Tensor, target: torch.Tensor, dice_weight: float = 1.0) -> torch.Tensor:
    """Cross-entropy + mean soft Dice over disc (rim ∪ cup), rim and cup.

    The rim term matters: without it, labelling the whole disc as cup costs little
    (disc Dice stays perfect), a degenerate solution seen on small synthetic images.
    """
    ce = F.cross_entropy(logits, target)
    prob = logits.softmax(dim=1)
    pairs = ((prob[:, 1] + prob[:, 2], (target >= 1).float()),
             (prob[:, 1], (target == 1).float()),
             (prob[:, 2], (target == 2).float()))
    dims = (1, 2)
    dice = torch.stack([(2 * (p * t).sum(dims) + 1.0) / (p.sum(dims) + t.sum(dims) + 1.0) for p, t in pairs])
    return ce + dice_weight * (1 - dice.mean())
