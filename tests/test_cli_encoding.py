"""Declared command-line entry points must print help on legacy Windows consoles."""
import os
import subprocess
import sys
from importlib.metadata import distribution

import pytest


@pytest.mark.parametrize("command", [ep.name for ep in distribution("hyunoptic").entry_points
                                    if ep.group == "console_scripts"])
def test_cli_help_on_windows_console_encoding(command):
    code = (
        "import sys; from importlib.metadata import distribution; "
        "entry = next(e for e in distribution('hyunoptic').entry_points if e.name == sys.argv[1]); "
        "sys.argv = [entry.name, '--help']; entry.load()()"
    )
    env = {**os.environ, "PYTHONIOENCODING": "cp1252:strict"}
    result = subprocess.run([sys.executable, "-c", code, command], env=env, capture_output=True)
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    assert b"usage:" in result.stdout
