"""PAPILA dataset ingestion. No dataset assets are packaged or downloaded."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

_IMAGE_NAME = re.compile(r"^(RET\d{3})(OD|OS)\.jpe?g$", re.IGNORECASE)


@dataclass(frozen=True)
class PapilaCase:
    patient_id: str
    eye: str  # OD is right eye, OS is left eye (NOT optic disc)
    image_path: Path
    contour_dir: Path

    @property
    def image_id(self) -> str:
        return f"{self.patient_id}{self.eye}"

    def contour_path(self, structure: str, expert: str) -> Path:
        if structure not in {"cup", "disc"}:
            raise ValueError("structure must be 'cup' or 'disc'")
        if expert not in {"exp1", "exp2"}:
            raise ValueError("expert must be 'exp1' or 'exp2'")
        return self.contour_dir / f"{self.image_id}_{structure}_{expert}.txt"


def _resolve_dirs(root: str | Path) -> tuple[Path, Path]:
    root = Path(root).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"PAPILA folder does not exist: {root}")
    # Published archives can use a hash-bearing top-level directory, not
    # necessarily PAPILA_DBv1. Only inspect this directory and its direct
    # children; do not recursively guess or mix data from multiple archives.
    candidates = [root, *(p for p in sorted(root.iterdir()) if p.is_dir())]
    matches = []
    for base in candidates:
        images = base / "FundusImages"
        contours = base / "ExpertsSegmentations" / "Contours"
        if images.is_dir() and contours.is_dir():
            matches.append((images, contours))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(
            "Multiple PAPILA datasets found; provide the exact extraction subfolder."
        )
    raise FileNotFoundError(
        "Expected a single directory with both FundusImages/ and "
        "ExpertsSegmentations/Contours/ under the provided directory or "
        "one of its direct children (hash-named archive roots are accepted)."
    )


def discover_cases(root: str | Path, require_complete: bool = True) -> list[PapilaCase]:
    """Index PAPILA image/annotation pairs without loading all full-resolution images.

    Strictly match known filenames; ignore duplicate annotation names with spaces.
    """
    image_dir, contour_dir = _resolve_dirs(root)
    result = []
    for image in sorted(image_dir.iterdir()):
        match = _IMAGE_NAME.fullmatch(image.name)
        if not match or not image.is_file():
            continue
        patient, eye = match.groups()
        case = PapilaCase(patient.upper(), eye.upper(), image, contour_dir)
        paths = [case.contour_path(s, e) for e in ("exp1", "exp2") for s in ("disc", "cup")]
        if require_complete and not all(p.is_file() for p in paths):
            continue
        result.append(case)
    return result


def load_image(case: PapilaCase) -> Image.Image:
    with Image.open(case.image_path) as image:
        image.load()
        return image.convert("RGB")


def load_contours(case: PapilaCase, expert: str) -> tuple[np.ndarray, np.ndarray]:
    """Load original full-resolution (x, y) points for optic disc and cup.

    Returns (disc_xy, cup_xy) as two N×2 float arrays; does not resize coordinates.
    """
    if expert not in ("exp1", "exp2"):
        raise ValueError("expert must be 'exp1' or 'exp2'")
    output = []
    for structure in ("disc", "cup"):
        path = case.contour_path(structure, expert)
        if not path.is_file():
            raise FileNotFoundError(f"Missing {structure} annotation: {path.name}")
        coords = np.loadtxt(path, dtype=np.float64, ndmin=2)
        if coords.ndim != 2 or coords.shape[1] != 2 or coords.shape[0] < 3:
            raise ValueError(f"Expected >=3 (x,y) contour points: {path.name}")
        if not np.isfinite(coords).all():
            raise ValueError(f"Non-finite contour coordinates: {path.name}")
        output.append(coords)
    return output[0], output[1]
