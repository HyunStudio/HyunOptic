"""The reader-role dashboard must not invent patient outcomes by default."""
from pathlib import Path
from streamlit.testing.v1 import AppTest

def test_empty_reader_page_has_no_performance_metrics():
    path = Path(__file__).resolve().parents[1] / "views" / "legacy_reader_roles.py"
    result = AppTest.from_file(str(path)).run(timeout=25)
    assert not result.exception, [str(x.message) for x in result.exception]
    assert len(result.metric) == 0
    assert len(result.info) >= 1
