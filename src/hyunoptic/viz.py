"""Image overlays for research review; never rescale source contour coordinates."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw


def overlay_contours(
    image: Image.Image,
    disc_xy: np.ndarray,
    cup_xy: np.ndarray,
    *, line_width: int = 5,
) -> Image.Image:
    """Red/cyan are augmented with solid/dashed distinction in the UI legend."""
    output = image.convert("RGB").copy()
    draw = ImageDraw.Draw(output)
    for pts, color in ((disc_xy, "#40E0D0"), (cup_xy, "#FF5C5C")):
        xy = [tuple(map(float, v)) for v in np.asarray(pts)]
        if len(xy) < 3:
            raise ValueError("At least three points required")
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
