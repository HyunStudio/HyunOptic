"""Experimental PyTorch optic-disc/cup segmentation (research only, NOT for clinical use).

Design: docs/superpowers/specs/2026-10-25-pytorch-optic-segmentation-design.md

Only ``model``, ``train``, ``inference`` and ``evaluate`` import PyTorch. Everything the
Streamlit workspace needs before a model is loaded (preprocessing contract, bundle
manifest verification, report schema) works without the optional ``ml`` extra.
"""
from __future__ import annotations

import importlib.util
import os

BUNDLE_SCHEMA = "hyunoptic.seg_bundle/v1"
REPORT_SCHEMA = "hyunoptic.seg_experiment_report/v1"
CLASSES = ("background", "disc_rim", "cup")  # disc = rim ∪ cup
RESEARCH_THRESHOLD = 0.10  # absolute vCDR error, research-only


def torch_available() -> bool:
    """False when PyTorch is absent, or when HYUNOPTIC_DISABLE_TORCH=1 (tests, lean installs)."""
    if os.environ.get("HYUNOPTIC_DISABLE_TORCH") == "1":
        return False
    return importlib.util.find_spec("torch") is not None
