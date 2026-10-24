"""Smoke test the research dashboard without any data uploaded."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

def test_study_page_displays_no_fabricated_results():
    page = Path(__file__).resolve().parents[1] / "pages" / "1_Study_Results.py"
    app = AppTest.from_file(str(page)).run(timeout=25)
    assert not app.exception, [str(x.message) for x in app.exception]
    assert len(app.metric) == 0  # Metrics require a real supplied v0.3 study report.
    assert len(app.info) >= 1  # Informational empty-report state is present.
