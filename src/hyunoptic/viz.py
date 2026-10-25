"""Image overlays for research review; never rescale source contour coordinates."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw


PALETTES = {
    "standard": {"disc": "#40E0D0", "cup": "#FF5C5C"},
    # Yellow/blue stay distinguishable for common colour-vision deficiencies.
    "high_contrast": {"disc": "#FFD400", "cup": "#00A2FF"},
}


def _dashed(draw: ImageDraw.ImageDraw, xy: list[tuple[float, float]], *,
            fill: str, width: int, dash: float, gap: float) -> None:
    """Draw a closed dashed polyline; the dash pattern continues across vertices."""
    on, remaining = True, dash
    for (x0, y0), (x1, y1) in zip(xy, xy[1:] + xy[:1]):
        length = float(np.hypot(x1 - x0, y1 - y0))
        pos = 0.0
        while pos < length:
            step = min(remaining, length - pos)
            if on:
                t0, t1 = pos / length, (pos + step) / length
                draw.line([(x0 + (x1 - x0) * t0, y0 + (y1 - y0) * t0),
                           (x0 + (x1 - x0) * t1, y0 + (y1 - y0) * t1)],
                          fill=fill, width=width)
            pos += step
            remaining -= step
            if remaining <= 1e-9:
                on = not on
                remaining = dash if on else gap


LINE_STYLES = {"solid": None, "dashed": (4.0, 2.5), "dotted": (1.2, 1.6)}


def draw_contour(draw: ImageDraw.ImageDraw, points: np.ndarray, *, color: str,
                 width: int, style: str = "solid") -> None:
    """Closed contour in a solid, dashed or dotted style (dash lengths scale with width)."""
    if style not in LINE_STYLES:
        raise ValueError(f"Unknown line style: {style}")
    xy = [tuple(map(float, v)) for v in np.asarray(points)]
    if len(xy) < 3:
        raise ValueError("At least three points required")
    pattern = LINE_STYLES[style]
    if pattern is None:
        draw.line(xy + [xy[0]], fill=color, width=width, joint="curve")
    else:
        _dashed(draw, xy, fill=color, width=width,
                dash=pattern[0] * width, gap=pattern[1] * width)


def overlay_contours(
    image: Image.Image,
    disc_xy: np.ndarray,
    cup_xy: np.ndarray,
    *, line_width: int = 5, palette: str = "standard", dashed_cup: bool = True,
) -> Image.Image:
    """Disc is solid, cup is dashed by default, so colour is never the only cue."""
    if palette not in PALETTES:
        raise ValueError(f"Unknown palette: {palette}")
    if line_width < 1:
        raise ValueError("line_width must be positive")
    colors = PALETTES[palette]
    output = image.convert("RGB").copy()
    draw = ImageDraw.Draw(output)
    draw_contour(draw, disc_xy, color=colors["disc"], width=line_width)
    draw_contour(draw, cup_xy, color=colors["cup"], width=line_width,
                 style="dashed" if dashed_cup else "solid")
    return output


def mask_outline(mask: np.ndarray, *, rays: int = 180) -> np.ndarray:
    """Approximate a filled binary mask by a star-shaped polygon around its centroid.

    Used only to DRAW mask annotations (optic disc/cup are near-convex); all
    measurements continue to use the original masks.
    """
    m = np.asarray(mask, dtype=bool)
    ys, xs = np.nonzero(m)
    if xs.size == 0:
        raise ValueError("Empty mask")
    cx, cy = xs.mean(), ys.mean()
    angles = np.arctan2(ys - cy, xs - cx)
    radii = np.hypot(xs - cx, ys - cy)
    bins = ((angles + np.pi) / (2 * np.pi) * rays).astype(int) % rays
    far = np.zeros(rays)
    np.maximum.at(far, bins, radii + 0.5)
    filled = far > 0
    if filled.sum() < 3:
        # A one/two-pixel prediction is still drawable. Enclose its pixel cells
        # rather than inventing a radial polygon or failing the entire viewer.
        left, right = float(xs.min()) - 0.5, float(xs.max()) + 0.5
        top, bottom = float(ys.min()) - 0.5, float(ys.max()) + 0.5
        return np.array([[left, top], [right, top], [right, bottom], [left, bottom]])
    centers = (np.arange(rays) + 0.5) / rays * 2 * np.pi - np.pi
    r = np.interp(centers, centers[filled], far[filled], period=2 * np.pi)
    return np.column_stack((cx + r * np.cos(centers), cy + r * np.sin(centers)))


def optic_crop(image: Image.Image, disc_xy: np.ndarray, *, padding: float = 0.7) -> Image.Image:
    """Crop near the disc on full-resolution overlay without changing measurements."""
    pts = np.asarray(disc_xy, dtype=np.float64)
    if pts.ndim != 2 or pts.shape[1] != 2:
        raise ValueError("disc_xy must be N×2")
    mins, maxs = np.min(pts, axis=0), np.max(pts, axis=0)
    margin = max(32.0, float(max(maxs - mins)) * padding)
    left = max(0, int(np.floor(mins[0] - margin)))
    top = max(0, int(np.floor(mins[1] - margin)))
    right = min(image.width, int(np.ceil(maxs[0] + margin + 1)))
    bottom = min(image.height, int(np.ceil(maxs[1] + margin + 1)))
    return image.crop((left, top, right, bottom))
