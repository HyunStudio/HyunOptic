"""Streamlit workspace smoke tests on the built-in synthetic geometry; no patient images."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def _review(tmp_path, monkeypatch) -> AppTest:
    monkeypatch.setenv("HYUNOPTIC_WORKSPACE", str(tmp_path / ".hyunoptic"))
    app = AppTest.from_file(APP, default_timeout=60).run()
    app.switch_page("views/image_review.py").run()
    assert not app.exception, [str(x.message) for x in app.exception]
    return app


def test_synthetic_demo_with_sensitivity_panel(tmp_path, monkeypatch):
    app = _review(tmp_path, monkeypatch)
    text = " ".join(m.value for m in app.markdown)
    assert "synthetic demo geometry" in text
    assert "Q95 |ΔvCDR|" in text and "Simulated vCDR SD" in text
    assert {b.label for b in app.get("download_button")} >= {"Download measurement JSON", "Download overlay PNG"}


def test_accessibility_controls_rerun_without_error(tmp_path, monkeypatch):
    app = _review(tmp_path, monkeypatch)
    app.toggle(key="pref_high_contrast").set_value(True)
    app.toggle(key="pref_dashed_cup").set_value(True)
    app.select_slider(key="pref_text_size").set_value("Large")
    app.run()
    assert not app.exception, [str(x.message) for x in app.exception]
    text = " ".join(m.value for m in app.markdown)
    assert "#FFD400" in text and "dashed" in text  # yellow disc, dashed cup in the legend
    assert "--hz-base:17px" in text
