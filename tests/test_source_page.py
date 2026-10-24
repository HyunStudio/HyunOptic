"""A blank research dashboard must not fabricate analysis results."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

def test_source_holdout_dashboard_empty_is_honest():
    page = Path(__file__).resolve().parents[1] / "pages" / "5_Source_Holdout.py"
    app = AppTest.from_file(str(page)).run(timeout=25)
    assert not app.exception, [str(e.message) for e in app.exception]
    assert len(app.metric) == 0
    assert len(app.info) >= 1
