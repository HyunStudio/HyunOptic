"""Unified image access for PAPILA (contours), Chákṣu Test (five-expert masks) and
the built-in synthetic geometry demo, plus overlay rendering and per-image metrics."""
from __future__ import annotations

import zipfile
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance

from ..chaksu import EXPERTS as CHAKSU_EXPERTS, load_test_case, scan_test_archive
from ..mask_features import mask_features
from ..measure import dice, measure_masks, polygon_mask
from ..papila import discover_cases, load_contours, load_image
from ..viz import draw_contour, mask_outline
from .theme import CUP_COLOR, DISC_COLOR, EXPERT_COLORS, HIGH_CONTRAST

SYNTHETIC = "Synthetic demo"


@dataclass(frozen=True)
class CaseRef:
    dataset: str          # "PAPILA", "Chákṣu" or SYNTHETIC
    case_id: str          # image identifier shown to the user
    group: str            # PAPILA patient, Chákṣu camera, or "demo"


@dataclass
class Reader:
    label: str            # "Expert 1" ...
    disc: np.ndarray      # boolean masks at full resolution
    cup: np.ndarray
    disc_xy: np.ndarray   # outline points for drawing
    cup_xy: np.ndarray


def list_cases(dataset: str, location: str) -> list[CaseRef]:
    if dataset == SYNTHETIC:
        return [CaseRef(SYNTHETIC, f"DEMO-{i + 1}", "demo") for i in range(3)]
    if dataset == "PAPILA":
        return [CaseRef("PAPILA", c.image_id, c.patient_id) for c in discover_cases(location)]
    if dataset == "Chákṣu":
        cases, _ = scan_test_archive(location)
        return [CaseRef("Chákṣu", c.case_id, c.camera) for c in cases]
    raise ValueError(f"Unknown dataset {dataset}")


def _ellipse(cx, cy, rx, ry, shift=0.0, n=120):
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return np.column_stack((cx + shift + rx * np.cos(t), cy + ry * np.sin(t)))


def _synthetic(index: int) -> tuple[Image.Image, list[Reader]]:
    """Artificial geometry only; never presented as a retinal photograph or a patient."""
    w, h = 720, 540
    img = Image.new("RGB", (w, h), "#120a06")
    d = ImageDraw.Draw(img)
    d.ellipse((60, 10, 660, 530), fill="#8a3b1c")
    d.ellipse((150, 70, 570, 470), fill="#a24a22")
    cx, cy = 360 + 25 * (index - 1), 270
    d.ellipse((cx - 85, cy - 95, cx + 85, cy + 95), fill="#d9894e")
    d.ellipse((cx - 45, cy - 52, cx + 45, cy + 52), fill="#f1c48c")
    readers = []
    geometry = [((88, 98, 0), (42 + 8 * index, 50 + 6 * index, 0)),
                ((84, 95, 4), (46 + 8 * index, 47 + 6 * index, 3))]
    for k, ((drx, dry, ds), (crx, cry, cs)) in enumerate(geometry):
        disc_xy = _ellipse(cx, cy, drx, dry, ds)
        cup_xy = _ellipse(cx + 6, cy - 4, crx, cry, cs)
        readers.append(Reader(f"Expert {k + 1}", polygon_mask(disc_xy, img.size),
                              polygon_mask(cup_xy, img.size), disc_xy, cup_xy))
    return img, readers


def load_case(ref: CaseRef, location: str) -> tuple[Image.Image, list[Reader]]:
    if ref.dataset == SYNTHETIC:
        return _synthetic(int(ref.case_id.split("-")[1]) - 1)
    if ref.dataset == "PAPILA":
        case = next(c for c in discover_cases(location) if c.image_id == ref.case_id)
        image = load_image(case)
        readers = []
        for k, expert in enumerate(("exp1", "exp2")):
            disc_xy, cup_xy = load_contours(case, expert)
            readers.append(Reader(f"Expert {k + 1}", polygon_mask(disc_xy, image.size),
                                  polygon_mask(cup_xy, image.size), disc_xy, cup_xy))
        return image, readers
    cases, _ = scan_test_archive(location)
    case = next(c for c in cases if c.case_id == ref.case_id)
    with zipfile.ZipFile(location) as zf:
        image, masks = load_test_case(zf, case, readers=CHAKSU_EXPERTS)
    readers = []
    for k, expert in enumerate(CHAKSU_EXPERTS):
        disc, cup = masks[(expert, "disc")], masks[(expert, "cup")]
        readers.append(Reader(f"Expert {k + 1}", disc, cup, mask_outline(disc), mask_outline(cup)))
    return image, readers


def adjust(image: Image.Image, brightness: int, contrast: int) -> Image.Image:
    """Display-only adjustment (−100…100); measurements always use the original pixels."""
    out = image
    if brightness:
        out = ImageEnhance.Brightness(out).enhance(1 + brightness / 100)
    if contrast:
        out = ImageEnhance.Contrast(out).enhance(1 + contrast / 100)
    return out


def render_overlay(image: Image.Image, readers: list[Reader], *, experts: list[int],
                   show_disc: bool = True, show_cup: bool = True, compare: bool = False,
                   high_contrast: bool = False, dashed_cup: bool = False,
                   thickness: int = 2) -> tuple[Image.Image, list[tuple[str, str, str]]]:
    """Return the overlay and a legend of (label, colour, line style).

    Single view: the first selected expert, disc solid and cup solid/dashed.
    Comparison: the first selected expert in disc/cup colours (solid); every
    other selected expert in its own colour, disc dashed and cup dotted, so the
    experts differ by line style as well as colour.
    """
    # Scale with disc size so lines look alike after zooming on any resolution.
    disc_span = float(max(np.ptp(r.disc_xy[:, 1]) for r in readers))
    width = max(1, round(int(thickness) * disc_span / 110))
    out = image.convert("RGB").copy()
    draw = ImageDraw.Draw(out)
    legend: list[tuple[str, str, str]] = []
    disc_c, cup_c = ((HIGH_CONTRAST["disc"], HIGH_CONTRAST["cup"]) if high_contrast
                     else (DISC_COLOR, CUP_COLOR))
    chosen = [i for i in experts if 0 <= i < len(readers)]
    if not compare:
        chosen = chosen[:1]
    for order, idx in enumerate(chosen):
        r = readers[idx]
        if order == 0:
            items = [("Disc", r.disc_xy, disc_c, "solid"),
                     ("Cup", r.cup_xy, cup_c, "dashed" if dashed_cup else "solid")]
        else:
            color = EXPERT_COLORS[idx % len(EXPERT_COLORS)]
            items = [("Disc", r.disc_xy, color, "dashed"), ("Cup", r.cup_xy, color, "dotted")]
        for name, pts, color, style in items:
            if (name == "Disc" and not show_disc) or (name == "Cup" and not show_cup):
                continue
            draw_contour(draw, pts, color=color, width=width, style=style)
            legend.append((f"{name} ({r.label})", color, style))
    return out, legend


def crop_to_disc(image: Image.Image, readers: list[Reader], padding: float = 0.9) -> Image.Image:
    pts = np.vstack([r.disc_xy for r in readers])
    lo, hi = pts.min(axis=0), pts.max(axis=0)
    margin = max(24.0, float((hi - lo).max()) * padding)
    box = (max(0, int(lo[0] - margin)), max(0, int(lo[1] - margin)),
           min(image.width, int(hi[0] + margin)), min(image.height, int(hi[1] + margin)))
    return image.crop(box)


def case_metrics(image: Image.Image, readers: list[Reader], a: int = 0, b: int = 1) -> dict:
    """Measurements for the selected expert pair; candidate features use expert ``a`` only."""
    ra = readers[a]
    ma = measure_masks(ra.disc, ra.cup)
    result = {"a": ra.label, "measure_a": ma.to_dict(), "features": None, "feature_error": None}
    try:
        result["features"] = mask_features(image, ra.disc, ra.cup)
    except ValueError as exc:
        result["feature_error"] = str(exc)
    if b is not None and 0 <= b < len(readers) and b != a:
        rb = readers[b]
        mb = measure_masks(rb.disc, rb.cup)
        result.update({
            "b": rb.label, "measure_b": mb.to_dict(),
            "abs_vcdr_difference": abs(ma.vertical_cdr - mb.vertical_cdr),
            "disc_dice": dice(ra.disc, rb.disc), "cup_dice": dice(ra.cup, rb.cup),
        })
    all_v = [measure_masks(r.disc, r.cup).vertical_cdr for r in readers]
    result["all_reader_vcdr"] = all_v
    return result


def thumbnail(image: Image.Image, size: int = 120) -> Image.Image:
    thumb = image.copy()
    thumb.thumbnail((size, size))
    return thumb
