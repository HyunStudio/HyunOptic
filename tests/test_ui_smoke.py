"""Streamlit synthetic demo smoke test; uses no patient images."""
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_synthetic_demo_with_sensitivity_panel():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=25)
    assert not app.exception, [str(x.message) for x in app.exception]
    assert len(app.metric) >= 7
    assert any("Sensitivity" in x.label or "vCDR" in x.label for x in app.metric)


def test_accessibility_controls_rerun_without_error():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run(timeout=25)
    toggles = {t.label: t for t in app.sidebar.toggle}
    toggles["High-contrast contour colours"].set_value(True)
    toggles["Dashed cup outline"].set_value(False)
    app.sidebar.select_slider[0].set_value("Large")
    app.run(timeout=25)
    assert not app.exception, [str(x.message) for x in app.exception]
    assert len(app.metric) >= 7
