"""Local workspace: dataset paths, analysis runs and an integrity-check history.

Everything is stored on the user's computer (default ``.hyunoptic/`` in the
working directory, or the folder named by ``HYUNOPTIC_WORKSPACE``). No network.
"""
from __future__ import annotations

import json
import os
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ..chaksu import scan_test_archive
from ..papila import discover_cases

WORKSPACE_ENV = "HYUNOPTIC_WORKSPACE"
SYNTHETIC_MARKER = "SYNTHETIC_DEMO_DATA.txt"


def workspace_dir() -> Path:
    return Path(os.environ.get(WORKSPACE_ENV, ".hyunoptic")).expanduser()


@dataclass
class Workspace:
    papila_root: str = ""
    papila_zip: str = ""
    chaksu_zip: str = ""
    reports_dir: str = "reports"
    seed: int = 42
    draws: int = 500
    bootstrap_draws: int = 1000

    @classmethod
    def load(cls) -> "Workspace":
        path = workspace_dir() / "workspace.json"
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        try:
            return cls(**known)
        except TypeError:
            return cls()

    def save(self) -> Path:
        folder = workspace_dir()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / "workspace.json"
        path.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")
        return path


@dataclass
class DatasetStatus:
    name: str
    role: str
    configured: bool = False
    connected: bool = False
    n_images: int = 0
    n_patients: int | None = None
    n_experts: int = 0
    groups: dict = field(default_factory=dict)
    synthetic: bool = False
    location: str = ""
    error: str = ""

    @property
    def state(self) -> str:
        if not self.configured:
            return "Not configured"
        return "Connected" if self.connected else "Error"


def papila_status(root: str) -> DatasetStatus:
    status = DatasetStatus("PAPILA", "Internal development (patient-disjoint)", n_experts=2,
                           location=root)
    if not root:
        return status
    status.configured = True
    try:
        cases = discover_cases(root)
    except (OSError, ValueError) as exc:
        status.error = str(exc)
        return status
    status.connected = bool(cases)
    status.n_images = len(cases)
    status.n_patients = len({c.patient_id for c in cases})
    status.groups = {"OD (right eye)": sum(c.eye == "OD" for c in cases),
                     "OS (left eye)": sum(c.eye == "OS" for c in cases)}
    base = Path(root).expanduser()
    status.synthetic = (base / SYNTHETIC_MARKER).is_file() or any(
        (p / SYNTHETIC_MARKER).is_file() for p in base.glob("*") if p.is_dir())
    if not cases:
        status.error = "No complete image + exp1/exp2 contour sets found."
    return status


def chaksu_status(archive: str) -> DatasetStatus:
    status = DatasetStatus("Chákṣu", "External test (frozen model)", n_experts=5,
                           location=archive)
    if not archive:
        return status
    status.configured = True
    try:
        cases, _ = scan_test_archive(archive)
        with zipfile.ZipFile(archive) as zf:
            status.synthetic = any(n.endswith(SYNTHETIC_MARKER) for n in zf.namelist())
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        status.error = str(exc)
        return status
    status.connected = bool(cases)
    status.n_images = len(cases)
    status.groups = {cam: sum(c.camera == cam for c in cases) for cam in ("bosch", "forus", "remidio")}
    if not cases:
        status.error = "No Test images with all five experts' masks were found."
    return status


# --- analysis runs -----------------------------------------------------------

def _read_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def find_runs(reports_dir: str | Path) -> list[Path]:
    """Folders made by hyunoptic-pipeline (they hold pipeline_manifest.json), newest first."""
    base = Path(reports_dir).expanduser()
    if not base.is_dir():
        return []
    found = {p.parent for p in base.glob("pipeline_manifest.json")}
    found |= {p.parent for p in base.glob("*/pipeline_manifest.json")}
    found |= {p.parent for p in base.glob("*/*/pipeline_manifest.json")}
    return sorted(found, key=lambda p: (p / "pipeline_manifest.json").stat().st_mtime, reverse=True)


@dataclass
class RunData:
    folder: Path | None
    manifest: dict | None = None
    inventory_counts: dict | None = None
    inventory_complete: bool | None = None
    lock: dict | None = None
    source: dict | None = None
    source_rows: list | None = None
    audit: dict | None = None
    external: dict | None = None
    external_rows: list | None = None
    evidence: dict | None = None
    sources: dict | None = None

    @property
    def label(self) -> str:
        return self.folder.name if self.folder else "Uploaded files"

    @property
    def partial(self) -> bool:
        flags = []
        if self.source is not None:
            flags.append(self.source.get("partial_or_unverified", True))
        if self.external is not None:
            flags.append(self.external.get("partial_or_unverified_external", True))
        if self.inventory_complete is not None:
            flags.append(not self.inventory_complete)
        return any(flags) or not flags

    @property
    def lock_sha(self) -> str | None:
        return (self.lock or {}).get("sha256")


def load_run(folder: str | Path) -> RunData:
    """Load aggregate files plus local private rows (rows stay on this computer)."""
    base = Path(folder)
    run = RunData(base)
    run.manifest = _read_json(base / "pipeline_manifest.json")
    inventory = _read_json(base / "inventory.json")
    if inventory:
        run.inventory_counts = inventory.get("observed")
        run.inventory_complete = inventory.get("matches_full_published_shape")
    run.lock = _read_json(base / "model_lock.json")
    run.source = _read_json(base / "source_holdout" / "source_aggregate.json")
    private = _read_json(base / "source_holdout" / "source_private_cases.json")
    run.source_rows = private.get("cases") if private else None
    run.audit = _read_json(base / "chaksu_audit" / "audit_aggregate.json")
    run.external = _read_json(base / "external" / "external_aggregate.json")
    private = _read_json(base / "external" / "external_private_cases.json")
    run.external_rows = private.get("rows") if private else None
    run.evidence = _read_json(base / "evidence_review.json")
    run.sources = _read_json(base / "sources.json")
    return run


def run_from_uploads(source: dict | None = None, external: dict | None = None) -> RunData:
    run = RunData(None)
    for data in (source, external):
        if data is not None and data.get("project") != "HyunOptic":
            raise ValueError("Not a HyunOptic report")
    run.source, run.external = source, external
    return run


# --- integrity / export history ----------------------------------------------

def _history_path() -> Path:
    return workspace_dir() / "history.json"


def read_history(kind: str | None = None, limit: int = 20) -> list[dict]:
    try:
        entries = json.loads(_history_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(entries, list):
        return []
    rows = [e for e in entries if isinstance(e, dict) and (kind is None or e.get("kind") == kind)]
    return rows[-limit:][::-1]


def append_history(kind: str, **fields) -> dict:
    entry = {"kind": kind, "time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"), **fields}
    try:
        entries = json.loads(_history_path().read_text(encoding="utf-8"))
        if not isinstance(entries, list):
            entries = []
    except (OSError, ValueError):
        entries = []
    entries.append(entry)
    path = _history_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries[-500:], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return entry
