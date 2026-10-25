"""Image-only inference adapter used by the CLI evaluator and the Streamlit page.

``Predictor.predict`` receives a fundus image and nothing else: no expert contour, mask or
expert-derived crop can enter. vCDR is computed with the shared ``measure_masks`` code.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import torch
from PIL import Image

from ..measure import measure_masks
from . import preprocess
from .bundle import Bundle, load_state_dict
from .model import build


@dataclass
class Prediction:
    status: str                       # "ok", "invalid_geometry" or "error"
    image_size: tuple[int, int]
    labels: np.ndarray | None = None  # class map at ORIGINAL resolution
    errors: list[str] = field(default_factory=list)
    measurement: dict | None = None   # from the shared measurement library
    preprocessing: dict = field(default_factory=dict)
    run_id: str = ""
    weights_sha256: str = ""

    @property
    def disc(self) -> np.ndarray | None:
        return None if self.labels is None else self.labels >= 1

    @property
    def cup(self) -> np.ndarray | None:
        return None if self.labels is None else self.labels == 2


class Predictor:
    def __init__(self, bundle: Bundle):
        self.bundle = bundle
        self.model = build(bundle.manifest["architecture"])
        self.model.load_state_dict(load_state_dict(bundle), strict=True)
        self.model.eval()
        self.size = bundle.image_size

    @torch.no_grad()
    def labels_at_model_resolution(self, arrays: np.ndarray) -> np.ndarray:
        """Batch of uint8 N×S×S×3 letterboxed images → N×S×S post-processed class maps."""
        x = torch.from_numpy(np.stack([preprocess.normalise(a) for a in arrays]))
        raw = self.model(x).argmax(dim=1).numpy().astype(np.uint8)
        return np.stack([preprocess.postprocess(r) for r in raw])

    def predict(self, image: Image.Image) -> Prediction:
        size = (image.width, image.height)
        meta = {"method": preprocess.METHOD, "postprocessing": "largest_disc_component_v1"}
        try:
            arr, lb = preprocess.image_array(image, self.size)
            meta.update(lb.to_dict())
            small = self.labels_at_model_resolution(arr[None])[0]
            labels = preprocess.to_original(small, lb)
        except (ValueError, OSError, RuntimeError) as exc:
            return Prediction("error", size, errors=[str(exc)], preprocessing=meta,
                              run_id=self.bundle.run_id, weights_sha256=self.bundle.weights_sha256)
        pred = Prediction("ok", size, labels, preprocessing=meta, run_id=self.bundle.run_id,
                          weights_sha256=self.bundle.weights_sha256)
        if not pred.disc.any() or not pred.cup.any():
            pred.status = "invalid_geometry"
            pred.errors.append("Predicted " + ("disc" if not pred.disc.any() else "cup") + " is empty")
            return pred
        try:
            pred.measurement = measure_masks(pred.disc, pred.cup).to_dict()
        except ValueError as exc:
            pred.status = "invalid_geometry"
            pred.errors.append(str(exc))
        return pred
