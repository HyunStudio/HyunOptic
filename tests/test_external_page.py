"""External dashboard does not make up test-set scores when no report is loaded."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

def test_empty_external_dashboard_displays_no_results():
    page=Path(__file__).resolve().parents[1]/"pages"/"4_External_Validation.py"
    app=AppTest.from_file(str(page)).run(timeout=25)
    assert not app.exception, [str(e.message) for e in app.exception]
    assert len(app.metric)==0
    assert len(app.info)>0
