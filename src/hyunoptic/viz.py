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
    for pts, color, dashed in ((disc_xy, colors["disc"], False),
                               (cup_xy, colors["cup"], dashed_cup)):
        xy = [tuple(map(float, v)) for v in np.asarray(pts)]
        if len(xy) < 3:
            raise ValueError("At least three points required")
        if dashed:
            _dashed(draw, xy, fill=color, width=line_width,
                    dash=4.0 * line_width, gap=2.5 * line_width)
        else:
            draw.line(xy + [xy[0]], fill=color, width=line_width, joint="curve")
    return output


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
