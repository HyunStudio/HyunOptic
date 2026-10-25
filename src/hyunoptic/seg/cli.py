"""hyunoptic-seg: offline, explicit training / evaluation / prediction (research only)."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import torch_available
from .bundle import BundleError, verify_bundle


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="HyunOptic PyTorch optic disc/cup segmentation (research only; "
                                            "NOT for clinical use). Requires: pip install -e '.[ml]'")
    sub = p.add_subparsers(dest="command", required=True)
    t = sub.add_parser("train", help="Train on PAPILA development, select on validation (expert 1 only)")
    t.add_argument("--papila-root", type=Path, required=True)
    t.add_argument("--output", type=Path, required=True, help="NEW bundle folder, e.g. models/unet_run1")
    t.add_argument("--image-size", type=int, default=384)
    t.add_argument("--epochs", type=int, default=40)
    t.add_argument("--batch-size", type=int, default=8)
    t.add_argument("--lr", type=float, default=1e-3)
    t.add_argument("--weight-decay", type=float, default=1e-4)
    t.add_argument("--base-channels", type=int, default=16)
    t.add_argument("--depth", type=int, default=4)
    t.add_argument("--seed", type=int, default=42)
    t.add_argument("--split-seed", type=int, default=42, help="Same seed as the QC protocol by default")
    t.add_argument("--device", default="auto", help="auto, cpu or cuda")
    t.add_argument("--allow-partial", action="store_true", help="Synthetic fixtures or subsets ONLY")
    e = sub.add_parser("evaluate", help="Evaluate a frozen bundle (PAPILA holdout once; Chaksu exploratory)")
    e.add_argument("--bundle", type=Path, required=True)
    e.add_argument("--papila-root", type=Path)
    e.add_argument("--chaksu-test-zip", type=Path, help="Exploratory external analysis")
    e.add_argument("--exploratory-rerun", action="store_true",
                   help="Repeat an already evaluated holdout; recorded as exploratory")
    pr = sub.add_parser("predict", help="Image-only prediction for one local image (JSON to stdout)")
    pr.add_argument("--bundle", type=Path, required=True)
    pr.add_argument("--image", type=Path, required=True)
    v = sub.add_parser("verify", help="Check a bundle's schema and SHA-256 without loading PyTorch")
    v.add_argument("--bundle", type=Path, required=True)
    a = p.parse_args(argv)

    if a.command == "verify":
        try:
            bundle = verify_bundle(a.bundle)
        except BundleError as exc:
            print(f"REJECTED: {exc}")
            return 2
        print(json.dumps({"run_id": bundle.run_id, "weights_sha256": bundle.weights_sha256,
                          "synthetic": bundle.synthetic, "partial": bundle.partial}, indent=2))
        return 0
    if not torch_available():
        p.error("PyTorch is not installed. Install the optional extra: pip install -e '.[ml]'")
    try:
        if a.command == "train":
            from .train import train

            def show(row):
                print(f"epoch {row['epoch']:>3}  loss {row['train_loss']:.4f}  val disc {row['val_disc_dice']:.3f}  "
                      f"val cup {row['val_cup_dice']:.3f}  ({row['seconds']}s)")
            out = train(a.papila_root, a.output, image_size=a.image_size, epochs=a.epochs,
                        batch_size=a.batch_size, lr=a.lr, weight_decay=a.weight_decay,
                        base_channels=a.base_channels, depth=a.depth, seed=a.seed, split_seed=a.split_seed,
                        allow_partial=a.allow_partial, device=a.device, progress=show)
            bundle = verify_bundle(out)
            print(f"Bundle: {out}  run {bundle.run_id}  best epoch {bundle.manifest['training']['best_epoch']}")
            print("The holdout has not been touched. Evaluate it once with `hyunoptic-seg evaluate`.")
        elif a.command == "evaluate":
            from .evaluate import evaluate_chaksu, evaluate_holdout
            bundle = verify_bundle(a.bundle)
            if a.papila_root is None and a.chaksu_test_zip is None:
                p.error("Pass --papila-root (internal holdout) and/or --chaksu-test-zip (exploratory)")
            if a.papila_root is not None:
                print("Holdout report:", evaluate_holdout(bundle, a.papila_root, exploratory_rerun=a.exploratory_rerun))
            if a.chaksu_test_zip is not None:
                print("Exploratory Chaksu report:", evaluate_chaksu(bundle, a.chaksu_test_zip))
        else:
            from PIL import Image

            from .inference import Predictor
            bundle = verify_bundle(a.bundle)
            with Image.open(a.image) as img:
                pred = Predictor(bundle).predict(img.convert("RGB"))
            print(json.dumps({"status": pred.status, "errors": pred.errors, "image_size": pred.image_size,
                              "measurement": pred.measurement, "run_id": pred.run_id,
                              "weights_sha256": pred.weights_sha256, "preprocessing": pred.preprocessing,
                              "note": "Research only; predicted vCDR is not a diagnosis."}, indent=2))
    except (BundleError, OSError, ValueError) as exc:
        p.error(str(exc))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
