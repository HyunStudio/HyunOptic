"""Immutable local inference bundle: manifest + config + split + weights, verified by SHA-256.

Verification needs no PyTorch, so the UI can refuse a bad bundle before importing it.
Weights are a plain ``state_dict`` loaded with ``torch.load(weights_only=True)``; arbitrary
pickles, other file names and paths outside the bundle folder are rejected.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from . import BUNDLE_SCHEMA

MANIFEST = "bundle_manifest.json"
WEIGHTS = "weights.pt"
CONFIG = "config.json"
SPLIT = "split_manifest.json"
HISTORY = "history.json"
REQUIRED = ("schema", "run_id", "created_utc", "software_version", "architecture", "preprocessing",
            "postprocessing", "training", "files", "data_status", "permitted_use")
_SAFE_NAME = re.compile(r"^[A-Za-z0-9_.-]+$")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


class BundleError(ValueError):
    """A bundle failed a verification gate; the message says which one and how to fix it."""


@dataclass(frozen=True)
class Bundle:
    folder: Path
    manifest: dict

    @property
    def identity(self) -> str:
        """Canonical complete manifest identity, including all verified config hashes."""
        canonical = json.dumps(self.manifest, sort_keys=True, separators=(",", ":"),
                               ensure_ascii=False, allow_nan=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @property
    def run_id(self) -> str:
        return self.manifest["run_id"]

    @property
    def weights_sha256(self) -> str:
        return self.manifest["files"][WEIGHTS]

    @property
    def synthetic(self) -> bool:
        return bool(self.manifest["data_status"].get("synthetic"))

    @property
    def partial(self) -> bool:
        return bool(self.manifest["data_status"].get("partial"))

    @property
    def image_size(self) -> int:
        return int(self.manifest["preprocessing"]["image_size"])


def _validate_contract(manifest: dict) -> None:
    """Refuse contracts the fixed inference implementation cannot execute faithfully."""
    for key in ("run_id", "created_utc", "software_version", "permitted_use"):
        if not isinstance(manifest[key], str) or not manifest[key].strip():
            raise BundleError(f"Invalid {key}: expected a nonempty string")
    for key in ("architecture", "preprocessing", "training", "data_status"):
        if not isinstance(manifest[key], dict):
            raise BundleError(f"Invalid {key}: expected an object")
    arch = manifest["architecture"]
    if (arch.get("name") != "unet_small_v1" or
            any(type(arch.get(key)) is not int or arch[key] != 3 for key in ("in_channels", "n_classes"))):
        raise BundleError("Unsupported architecture: expected unet_small_v1 with 3 input channels and 3 classes")
    for key, minimum in (("base_channels", 4), ("depth", 2)):
        if type(arch.get(key)) is not int or arch[key] < minimum:
            raise BundleError(f"Invalid architecture {key}")
    pre = manifest["preprocessing"]
    size = pre.get("image_size")
    if type(size) is not int or size < 32 or size % 16 or arch["depth"] >= size.bit_length() or size % (2 ** arch["depth"]):
        raise BundleError("Unsupported preprocessing image_size: must be >=32, multiple of 16 and compatible with depth")
    for key, expected in (("method", "letterbox_v1"), ("image_interpolation", "bilinear"),
                          ("mask_interpolation", "nearest")):
        if pre.get(key) != expected:
            raise BundleError(f"Unsupported preprocessing {key}")
    for key, expected in (("mean", [0.5] * 3), ("std", [0.25] * 3)):
        value = pre.get(key)
        if (not isinstance(value, list) or len(value) != 3 or
                any(type(v) not in (int, float) for v in value) or value != expected):
            raise BundleError(f"Unsupported preprocessing {key}: expected {expected}")
    if manifest["postprocessing"] not in (
            "largest_disc_component_v1", "largest_disc_component_v1 (largest 4-connected disc, cup inside it)"):
        raise BundleError("Unsupported postprocessing")
    for key in ("synthetic", "partial"):
        if type(manifest["data_status"].get(key)) is not bool:
            raise BundleError(f"Invalid data_status {key}: expected boolean")
    try:
        json.dumps(manifest, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise BundleError("Manifest contains non-finite or invalid JSON values") from exc


def verify_bundle(folder: str | Path) -> Bundle:
    base = Path(folder).expanduser()
    path = base / MANIFEST
    if not path.is_file():
        raise BundleError(f"No {MANIFEST} in {base}. Train a model with `hyunoptic-seg train` first.")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BundleError(f"Unreadable manifest: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("schema") != BUNDLE_SCHEMA:
        raise BundleError(f"Unsupported bundle schema (expected {BUNDLE_SCHEMA}).")
    missing = [k for k in REQUIRED if k not in manifest]
    if missing:
        raise BundleError("Manifest is missing fields: " + ", ".join(missing))
    _validate_contract(manifest)
    files = manifest["files"]
    if not isinstance(files, dict) or set(files) != {WEIGHTS, CONFIG, SPLIT, HISTORY}:
        raise BundleError("Manifest must list exactly weights.pt, config.json, split_manifest.json, history.json")
    for name, expected in files.items():
        if not _SAFE_NAME.match(name):
            raise BundleError(f"Unsafe file name in manifest: {name!r}")
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise BundleError(f"Invalid SHA-256 for {name}")
        target = base / name
        if target.resolve().parent != base.resolve():
            raise BundleError(f"Bundle file outside bundle folder: {name}")
        if not target.is_file():
            raise BundleError(f"Bundle file missing: {name}")
        try:
            actual = file_sha256(target)
        except OSError as exc:
            raise BundleError(f"Cannot read bundle file {name}: {exc}") from exc
        if actual != expected:
            raise BundleError(f"SHA-256 mismatch for {name}: the file changed after training. "
                              "Re-train or restore the original bundle.")
    return Bundle(base, manifest)


def find_bundles(models_dir: str | Path) -> list[Path]:
    base = Path(models_dir).expanduser()
    if not base.is_dir():
        return []
    found = {p.parent for p in base.glob(MANIFEST)} | {p.parent for p in base.glob(f"*/{MANIFEST}")}
    return sorted(found, key=lambda p: (p / MANIFEST).stat().st_mtime, reverse=True)


def load_state_dict(bundle: Bundle):
    """Restricted load of the verified weights file (tensors only)."""
    import torch

    target = bundle.folder / WEIGHTS
    if file_sha256(target) != bundle.weights_sha256:  # re-check right before loading
        raise BundleError("Weights changed since verification")
    try:
        state = torch.load(target, map_location="cpu", weights_only=True)
    except Exception as exc:  # torch raises several unpickling error types
        raise BundleError(f"Weights refused by the restricted loader: {exc}") from exc
    if not isinstance(state, dict) or not all(isinstance(v, torch.Tensor) for v in state.values()):
        raise BundleError("Weights file is not a plain tensor state_dict")
    return state
