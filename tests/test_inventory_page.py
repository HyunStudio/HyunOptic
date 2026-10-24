"""Dataset Quality Streamlit page requires a user inventory, never fake statistics."""
from pathlib import Path
from streamlit.testing.v1 import AppTest


def test_no_inventory_no_metrics():
    page = Path(__file__).resolve().parents[1] / "pages" / "2_Dataset_Quality.py"
    result = AppTest.from_file(str(page)).run(timeout=25)
    assert not result.exception, [str(x.message) for x in result.exception]
    assert len(result.metric) == 0
    assert len(result.info) >= 1
