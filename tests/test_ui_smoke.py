"""Streamlit synthetic demo smoke test; uses no patient images."""
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_synthetic_demo_with_sensitivity_panel():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=25)
    assert not app.exception, [str(x.message) for x in app.exception]
    assert len(app.metric) >= 7
    assert any("Sensitivity" in x.label or "vCDR" in x.label for x in app.metric)
