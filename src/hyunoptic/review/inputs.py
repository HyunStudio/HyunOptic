"""Bounded image import with original-byte and EXIF-normalized pixel identity."""
from __future__ import annotations

import hashlib
import io
import json
import warnings

import numpy as np
from PIL import Image, ImageOps

MAX_INPUTS = 500
MAX_FILE_BYTES = 30 * 1024**2
MAX_TOTAL_BYTES = 2 * 1024**3
MAX_PIXELS = 25_000_000


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def decode_image(data: bytes) -> Image.Image:
    if len(data) > MAX_FILE_BYTES:
        raise ValueError('Input exceeds 30 MB')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in {'PNG', 'JPEG', 'TIFF'}:
                    raise ValueError('Only PNG, JPEG and single-frame TIFF are supported')
                if getattr(image, 'n_frames', 1) != 1:
                    raise ValueError('Multi-frame images are unsupported')
                if image.width * image.height > MAX_PIXELS:
                    raise ValueError('Input exceeds 25 megapixels')
                if image.mode not in {'RGB', 'L'}:
                    raise ValueError('Only RGB and grayscale L images are supported')
                return ImageOps.exif_transpose(image).convert('RGB').copy()
    except OSError as exc:
        raise ValueError('Image data cannot be decoded. Use a complete PNG, JPEG or single-frame TIFF image.') from exc


def inspect_input(data: bytes) -> dict:
    image = decode_image(data)
    array = np.asarray(image)
    identity = json.dumps({'size': image.size, 'mode': 'RGB'}, sort_keys=True).encode() + array.tobytes()
    return {'pixel_sha256': sha256(identity), 'width': image.width, 'height': image.height}
