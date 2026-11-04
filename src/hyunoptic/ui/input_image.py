"""Bounded single-frame image loading for local inference uploads; no ML dependency."""
from __future__ import annotations

import io
from pathlib import Path
from typing import BinaryIO

from PIL import Image, ImageOps, UnidentifiedImageError

MAX_BYTES = 25 * 1024 * 1024
MAX_PIXELS = 40_000_000


def load_input_image(source: bytes | str | Path | BinaryIO, *, max_bytes: int = MAX_BYTES,
                     max_pixels: int = MAX_PIXELS) -> Image.Image:
    """Return detached, EXIF-oriented RGB pixels after checking encoded/decode limits.

    Only ordinary 8-bit RGB and grayscale images are supported. Stacks/animations
    require explicit frame selection upstream and are refused here.
    """
    if isinstance(source, bytes):
        payload = source
    elif isinstance(source, (str, Path)):
        with Path(source).open('rb') as stream:
            payload = stream.read(max_bytes + 1)
    else:
        source.seek(0)
        payload = source.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise ValueError(f"Image exceeds {max_bytes} encoded bytes")
    try:
        with Image.open(io.BytesIO(payload)) as image:
            if image.width < 1 or image.height < 1 or image.width * image.height > max_pixels:
                raise ValueError(f"Image exceeds {max_pixels} pixels")
            if getattr(image, 'n_frames', 1) != 1:
                raise ValueError('Multi-frame images are unsupported; choose a single frame explicitly')
            if image.mode not in ('RGB', 'L'):
                raise ValueError(f"Unsupported image mode {image.mode}; use 8-bit RGB or L")
            return ImageOps.exif_transpose(image).convert('RGB').copy()
    except (Image.DecompressionBombError, UnidentifiedImageError) as exc:
        raise ValueError(f"Cannot decode image: {exc}") from exc
