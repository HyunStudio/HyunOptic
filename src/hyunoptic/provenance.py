"""Best-effort commit identity bound to this application's source checkout."""
from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess


def source_commit() -> str:
    """Return the full source Git commit, or ``unknown`` outside a verified checkout.

    A wheel, copied source tree, or enclosing unrelated repository cannot supply
    a source commit. Package version is reported separately by each consumer.
    """
    try:
        package = Path(__file__).resolve().parent
        if package.name != "hyunoptic" or package.parent.name != "src":
            return "unknown"
        root = package.parent.parent
        if not ((root / ".git").is_dir() or (root / ".git").is_file()):
            return "unknown"
        if not (package / "__init__.py").is_file():
            return "unknown"
        metadata = (root / "pyproject.toml").read_text(encoding="utf-8")
        project = re.search(r"(?ms)^\[project\]\s*\n(.*?)(?=^\[|\Z)", metadata)
        if project is None or not re.search(
                r'''(?m)^name\s*=\s*["']hyunoptic["']\s*(?:#.*)?$''', project[1]):
            return "unknown"

        # -C alone does not override inherited GIT_DIR/GIT_WORK_TREE or config.
        environment = {key: value for key, value in os.environ.items()
                       if not key.upper().startswith("GIT_")}

        def git(*arguments: str) -> str:
            return subprocess.check_output(
                ["git", "-C", str(root), "rev-parse", *arguments],
                text=True, stderr=subprocess.DEVNULL, timeout=5,
                env=environment,
            ).strip()

        toplevel = Path(git("--show-toplevel"))
        if not toplevel.is_absolute() or toplevel.resolve() != root:
            return "unknown"
        commit = git("--verify", "HEAD^{commit}")
        if re.fullmatch(r"(?:[0-9a-fA-F]{40}|[0-9a-fA-F]{64})", commit):
            return commit.lower()
    except (OSError, subprocess.SubprocessError, UnicodeError, ValueError):
        pass
    return "unknown"
