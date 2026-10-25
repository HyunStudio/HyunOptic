"""Explicit PyTorch training loop on PAPILA development patients (expert 1 targets only).

Checkpoint selection uses the validation split only; the holdout is never touched here.
Writes a NEW bundle folder: weights.pt, config.json, split_manifest.json, history.json and
bundle_manifest.json (SHA-256 of every file).
"""
from __future__ import annotations

import copy
import json
import math
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from .. import __version__
from ..inventory import inspect_papila
from ..pipeline import _git_commit
from ..source_fingerprint import papila_content_sha256
from ..ui.workspace import SYNTHETIC_MARKER
from . import BUNDLE_SCHEMA, CLASSES, preprocess
from .bundle import CONFIG, HISTORY, MANIFEST, SPLIT, WEIGHTS, file_sha256
from .data import TRAIN_READER, build_split_manifest, cases_for, training_example
from .model import ARCHITECTURE, UNet, segmentation_loss

AUGMENTATIONS = [
    "horizontal flip p=0.5 (image and mask)",
    "rotation ±10°, scale 0.9–1.1, translation ±5% (image bilinear, mask nearest, black fill)",
    "brightness ×0.9–1.1 and contrast ×0.9–1.1 (image only)",
]
PHOTOMETRIC_POLICIES = ("baseline_v1", "camera_robust_v2")
CAMERA_ROBUST_AUGMENTATIONS = AUGMENTATIONS[:2] + [
    "brightness x0.7-1.3 and contrast x0.7-1.3 (image only, foreground mean)",
    "independent RGB gains x0.65-1.35 and gamma 0.7-1.5 (image only)",
    "retain black pixels <=1/255 after spatial transforms; targets unchanged by photometry",
]
SELECTION_RULE = ("highest validation mean of per-image (disc Dice + cup Dice)/2 at model resolution, "
                  "post-processed predictions vs expert 1")


def dice(pred: np.ndarray, ref: np.ndarray) -> float:
    a, b = np.asarray(pred, bool), np.asarray(ref, bool)
    total = int(a.sum()) + int(b.sum())
    return 1.0 if total == 0 else float(2 * np.count_nonzero(a & b) / total)


def _augment(x: torch.Tensor, y: torch.Tensor, gen: torch.Generator, *,
             photometric_policy: str = "baseline_v1",
             photometric_gen: torch.Generator | None = None) -> tuple[torch.Tensor, torch.Tensor]:
    if photometric_policy not in PHOTOMETRIC_POLICIES:
        raise ValueError(f"Unknown photometric policy {photometric_policy!r}")
    robust = photometric_policy == "camera_robust_v2"
    if robust and photometric_gen is None:
        raise ValueError("camera_robust_v2 requires a separate photometric generator")
    b = x.shape[0]
    flip = torch.rand(b, generator=gen) < 0.5
    x = torch.where(flip[:, None, None, None], x.flip(-1), x)
    y = torch.where(flip[:, None, None], y.flip(-1), y)
    angle = (torch.rand(b, generator=gen) * 2 - 1) * math.radians(10)
    scale = 1 + (torch.rand(b, generator=gen) * 2 - 1) * 0.1
    shift = (torch.rand(b, 2, generator=gen) * 2 - 1) * 0.1  # ±5% of width in [-1, 1] coords
    cos, sin = torch.cos(angle) / scale, torch.sin(angle) / scale
    theta = torch.stack([torch.stack([cos, -sin, shift[:, 0]], 1), torch.stack([sin, cos, shift[:, 1]], 1)], 1)
    grid = F.affine_grid(theta, list(x.shape), align_corners=False)
    black = torch.tensor([(0 - m) / s for m, s in zip(preprocess.MEAN, preprocess.STD)]).view(1, 3, 1, 1)
    x = F.grid_sample(x - black, grid, mode="bilinear", padding_mode="zeros", align_corners=False) + black
    y = F.grid_sample(y[:, None].float(), grid, mode="nearest", padding_mode="zeros",
                      align_corners=False)[:, 0].long()
    mean = torch.tensor(preprocess.MEAN).view(1, 3, 1, 1)
    std = torch.tensor(preprocess.STD).view(1, 3, 1, 1)
    raw = x * std + mean
    strength = 0.3 if robust else 0.1
    # Keep these two legacy draws on gen: added photometry must not change
    # shuffle/spatial RNG progression compared with the same baseline seed.
    bright = 1 + (torch.rand(b, 1, 1, 1, generator=gen) * 2 - 1) * strength
    contrast = 1 + (torch.rand(b, 1, 1, 1, generator=gen) * 2 - 1) * strength
    if robust:
        foreground = raw.amax(dim=1, keepdim=True) > 1 / 255
        centre = (raw * foreground).sum(dim=(1, 2, 3), keepdim=True) / (
            3 * foreground.sum(dim=(1, 2, 3), keepdim=True).clamp_min(1))
    else:
        centre = raw.mean(dim=(1, 2, 3), keepdim=True)
    raw = ((raw * bright - centre) * contrast + centre).clamp(0, 1)
    if robust:
        gains = 0.65 + torch.rand(b, 3, 1, 1, generator=photometric_gen) * 0.7
        gamma = 0.7 + torch.rand(b, 1, 1, 1, generator=photometric_gen) * 0.8
        raw = (raw * gains).clamp(0, 1).pow(gamma)
        raw = torch.where(foreground, raw, torch.zeros_like(raw))
    return (raw - mean) / std, y


def _validate(model: torch.nn.Module, images: torch.Tensor, targets: np.ndarray, device: str,
              batch: int) -> tuple[float, float, float]:
    model.eval()
    disc, cup = [], []
    with torch.no_grad():
        for i in range(0, len(images), batch):
            raw = model(images[i:i + batch].to(device)).argmax(1).cpu().numpy().astype(np.uint8)
            for pred, ref in zip(raw, targets[i:i + batch]):
                p = preprocess.postprocess(pred)
                disc.append(dice(p >= 1, ref >= 1))
                cup.append(dice(p == 2, ref == 2))
    model.train()
    return float(np.mean(disc)), float(np.mean(cup)), float(np.mean([(a + b) / 2 for a, b in zip(disc, cup)]))


def _load(root, split_body, split, size):
    arrays, targets = [], []
    for case in cases_for(root, split_body, split):
        a, t = training_example(case, size)
        arrays.append(a)
        targets.append(t)
    if not arrays:
        raise ValueError(f"Empty {split} split")
    x = torch.from_numpy(np.stack([preprocess.normalise(a) for a in arrays]))
    return x, np.stack(targets)


def train(papila_root: str | Path, output_dir: str | Path, *, image_size: int = 384, epochs: int = 40,
          batch_size: int = 8, lr: float = 1e-3, weight_decay: float = 1e-4, base_channels: int = 16,
          depth: int = 4, seed: int = 42, split_seed: int = 42, allow_partial: bool = False,
          device: str = "auto", photometric_policy: str = "baseline_v1", progress=None) -> Path:
    if photometric_policy not in PHOTOMETRIC_POLICIES:
        raise ValueError(f"Unknown photometric policy {photometric_policy!r}")
    out = Path(output_dir)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError("Bundle folder is not empty; choose a NEW folder (bundles are immutable)")
    if epochs < 1 or batch_size < 1 or not 0 < lr < 1:
        raise ValueError("epochs and batch_size must be positive, lr in (0, 1)")
    if image_size % 2 ** depth:
        raise ValueError(f"image_size must be divisible by {2 ** depth} for depth {depth}")
    inventory = inspect_papila(papila_root)
    complete = bool(inventory["matches_full_published_shape"])
    if not complete and not allow_partial:
        raise ValueError("PAPILA inventory is incomplete (see hyunoptic-inventory). "
                         "--allow-partial is for synthetic fixtures or exploratory subsets only.")
    root = Path(papila_root).expanduser()
    synthetic = (root / SYNTHETIC_MARKER).is_file() or any(
        (p / SYNTHETIC_MARKER).is_file() for p in root.glob("*") if p.is_dir())
    device = ("cuda" if torch.cuda.is_available() else "cpu") if device == "auto" else device
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)
    gen = torch.Generator().manual_seed(seed)
    photometric_seed = (seed + 1_000_003) % (2 ** 63)
    photometric_gen = (torch.Generator().manual_seed(photometric_seed)
                       if photometric_policy == "camera_robust_v2" else None)

    split = build_split_manifest(papila_root, split_seed)
    body = split["manifest"]
    dev_x, dev_y = _load(papila_root, body, "development", image_size)
    val_x, val_y = _load(papila_root, body, "validation", image_size)
    balance = {name: float((dev_y == k).mean()) for k, name in enumerate(CLASSES)}

    arch = {"name": ARCHITECTURE, "in_channels": 3, "n_classes": len(CLASSES),
            "base_channels": base_channels, "depth": depth}
    model = UNet(3, len(CLASSES), base_channels, depth).to(device)
    optimiser = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimiser, T_max=epochs)
    targets = torch.from_numpy(dev_y.astype(np.int64))
    history, best, best_state, start = [], (-1.0, 0), None, time.perf_counter()
    for epoch in range(1, epochs + 1):
        tick = time.perf_counter()
        order = torch.randperm(len(dev_x), generator=gen)
        losses = []
        for i in range(0, len(order), batch_size):
            idx = order[i:i + batch_size]
            x, y = _augment(dev_x[idx], targets[idx], gen, photometric_policy=photometric_policy,
                            photometric_gen=photometric_gen)
            loss = segmentation_loss(model(x.to(device)), y.to(device))
            optimiser.zero_grad(set_to_none=True)
            loss.backward()
            optimiser.step()
            losses.append(float(loss.detach()))
        lr_now = optimiser.param_groups[0]["lr"]
        scheduler.step()
        d, c, score = _validate(model, val_x, val_y, device, batch_size)
        row = {"epoch": epoch, "train_loss": float(np.mean(losses)), "val_disc_dice": d,
               "val_cup_dice": c, "val_score": score, "lr": lr_now,
               "seconds": round(time.perf_counter() - tick, 2)}
        history.append(row)
        if score > best[0]:
            best, best_state = (score, epoch), copy.deepcopy(model.state_dict())
        if progress is not None:
            progress(row)

    out.mkdir(parents=True, exist_ok=True)
    torch.save({k: v.cpu() for k, v in best_state.items()}, out / WEIGHTS)
    config = {
        "architecture": arch, "image_size": image_size, "epochs": epochs, "batch_size": batch_size,
        "optimizer": {"name": "AdamW", "lr": lr, "weight_decay": weight_decay},
        "scheduler": "CosineAnnealingLR(T_max=epochs), stepped per epoch",
        "loss": "cross-entropy + mean soft Dice over disc (rim ∪ cup), rim and cup", "augmentations": AUGMENTATIONS,
        "seed": seed, "split_seed": split_seed, "device": device, "selection_rule": SELECTION_RULE,
    }
    if photometric_policy == "camera_robust_v2":
        config.update(photometric_policy=photometric_policy, photometric_generator_seed=photometric_seed,
                      augmentations=CAMERA_ROBUST_AUGMENTATIONS)
    (out / CONFIG).write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    (out / SPLIT).write_text(json.dumps(split, indent=2) + "\n", encoding="utf-8")
    (out / HISTORY).write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    created = datetime.now(timezone.utc)
    manifest = {
        "schema": BUNDLE_SCHEMA,
        "run_id": f"seg-{created:%Y%m%d-%H%M%S}-{file_sha256(out / WEIGHTS)[:8]}",
        "created_utc": created.isoformat(timespec="seconds"),
        "software_version": __version__, "git_commit": _git_commit(),
        "runtime": {"python": platform.python_version(), "torch": torch.__version__,
                    "numpy": np.__version__, "device": device,
                    "training_seconds": round(time.perf_counter() - start, 1)},
        "architecture": arch,
        "preprocessing": {"method": preprocess.METHOD, "image_size": image_size,
                          "mean": list(preprocess.MEAN), "std": list(preprocess.STD),
                          "image_interpolation": "bilinear", "mask_interpolation": "nearest"},
        "postprocessing": "largest_disc_component_v1 (largest 4-connected disc, cup inside it)",
        "training": {
            "dataset": "PAPILA", "reader": TRAIN_READER, "source_content_sha256": papila_content_sha256(papila_root),
            "source_inventory_fingerprint": inventory["inventory_sha256_of_paths_and_sizes_only"],
            "split_manifest_sha256": split["sha256"], "split_seed": split_seed,
            "n_images": {k: len(v) for k, v in body["splits"].items()},
            "n_patients": {k: len(v) for k, v in body["patients"].items()},
            "class_balance_development": balance, "selection_rule": SELECTION_RULE,
            "best_epoch": best[1], "best_validation_score": best[0], "epochs": epochs,
            "holdout_used_in_training_or_selection": False, "expert2_used": False,
        },
        "data_status": {"synthetic": synthetic, "partial": not complete, "inventory_complete": complete,
                        "n_images_discovered": inventory["observed"]["images"]},
        "permitted_use": "Research only. Not for clinical use, diagnosis or patient care. Local use only.",
        "files": {name: file_sha256(out / name) for name in (WEIGHTS, CONFIG, SPLIT, HISTORY)},
    }
    (out / MANIFEST).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return out
