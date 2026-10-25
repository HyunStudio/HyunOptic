"""One-command research chain: sources → inventory → freeze → source holdout →
Chákṣu preflight → external test → evidence gate → HTML report.

Every step calls the same functions as the individual CLIs, writes into one NEW
output folder, and records its status in ``pipeline_manifest.json``. Nothing is
uploaded. Passing every step is NOT scientific or clinical validation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .evidence_gate import review_evidence, save_evidence_review
from .external import run_external_test, save_external
from .external_qc import check_chaksu_archive, save_chaksu_audit
from .freeze import freeze_papila_model, save_lock
from .html_report import write_html_report
from .inventory import inspect_papila, save_inventory
from .source_holdout import evaluate_source, save_source_evaluation
from .source_integrity import save_integrity_report, verify_archive

# Files safe to share: aggregate outputs only (still review dataset terms first).
AGGREGATE_FILES = (
    "pipeline_manifest.json", "report.html", "model_lock.json",
    "source_holdout/source_aggregate.json", "source_holdout/source_summary.md",
    "chaksu_audit/audit_aggregate.json", "external/external_aggregate.json",
    "external/external_summary.md", "evidence_review.json", "sources.json",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "-C", str(Path(__file__).resolve().parents[2]), "rev-parse", "HEAD"],
            text=True, stderr=subprocess.DEVNULL, timeout=5).strip()
    except (OSError, subprocess.SubprocessError):
        return os.environ.get("GITHUB_SHA")


def run_pipeline(
    papila_root: str | Path, output_dir: str | Path, *,
    chaksu_test_zip: str | Path | None = None, papila_zip: str | Path | None = None,
    allow_partial: bool = False, verify_pixels: bool = False,
    seed: int = 42, draws: int = 500, bootstrap_draws: int = 1000,
    progress=None,
) -> dict:
    """``progress(name, status, detail)`` is called after every step, e.g. to update a UI."""
    out = Path(output_dir)
    if out.exists() and any(out.iterdir()):
        raise FileExistsError("Output folder is not empty; choose a NEW folder to preserve provenance")
    out.mkdir(parents=True, exist_ok=True)
    steps: list[dict] = []
    manifest = {
        "project": "HyunOptic", "version": __version__, "status": "research-only",
        "started_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_code_git_commit_if_available": _git_commit(),
        "settings": {"seed": seed, "draws": draws, "bootstrap_draws": bootstrap_draws,
                     "allow_partial": allow_partial, "verify_pixels": verify_pixels,
                     "chaksu_supplied": chaksu_test_zip is not None,
                     "papila_zip_supplied": papila_zip is not None},
        "steps": steps,
        "scientific_validity_established": False,
        "clinical_accuracy_established": False,
    }
    paths = {
        "sources": out / "sources.json", "inventory": out / "inventory.json",
        "lock": out / "model_lock.json", "source_dir": out / "source_holdout",
        "audit_dir": out / "chaksu_audit", "external_dir": out / "external",
        "evidence": out / "evidence_review.json", "report": out / "report.html",
    }
    loaded: dict[str, dict | None] = dict.fromkeys(
        ("inventory", "source", "audit", "external", "evidence"))

    def step(name: str, status: str, detail: str = "") -> None:
        steps.append({"name": name, "status": status, "detail": detail})
        if progress is not None:
            progress(name, status, detail)

    def run(name: str, action) -> bool:
        # An action returns its detail text, or (detail, complete) where
        # complete=False marks output that ran but is partial/unverified.
        try:
            outcome = action() or ""
        except (OSError, ValueError, KeyError, TypeError) as exc:
            step(name, "failed", f"{type(exc).__name__}: {exc}")
            return False
        detail, complete = outcome if isinstance(outcome, tuple) else (outcome, True)
        step(name, "passed" if complete else "incomplete", detail)
        return True

    # 1. Archive identity (optional; requires the original ZIP files).
    archives = [(z, d) for z, d in ((papila_zip, "PAPILA"), (chaksu_test_zip, "CHAKSU_TEST"))
                if z is not None]
    if archives:
        def sources():
            checks = [verify_archive(z, d) for z, d in archives]
            save_integrity_report(checks, paths["sources"])
            return ("; ".join(f"{c['dataset']} reference match: "
                              f"{c['matches_independent_public_reference']}" for c in checks),
                    all(c["matches_independent_public_reference"] for c in checks))
        run("archive_identity", sources)
    else:
        step("archive_identity", "skipped", "No --papila-zip / --chaksu-test-zip given")

    # 2. PAPILA inventory, required before anything is frozen.
    def inventory():
        report = inspect_papila(papila_root, verify_pixels=verify_pixels)
        save_inventory(report, paths["inventory"])
        loaded["inventory"] = report
        complete = report["matches_full_published_shape"]
        if not complete and not allow_partial:
            raise ValueError("PAPILA inventory is incomplete; see inventory.json "
                             "(--allow-partial is for synthetic fixtures only)")
        obs = report["observed"]
        return f"{obs['patients']} patients, {obs['images']} images, complete={complete}", complete
    ok = run("papila_inventory", inventory)

    # 3. Freeze on the patient-disjoint development split (exp1 only).
    if ok:
        def freeze():
            lock = freeze_papila_model(papila_root, seed=seed, draws=draws,
                                       allow_partial=allow_partial)
            save_lock(lock, paths["lock"])
            return f"lock sha256 {lock['sha256']}", not lock["model"]["source_is_partial"]
        ok = run("freeze_papila_development", freeze)
    else:
        step("freeze_papila_development", "skipped", "Inventory step failed")

    # 4. Same frozen mask score on PAPILA validation + holdout patients.
    if ok:
        def source():
            result, rows = evaluate_source(papila_root, paths["lock"],
                                           allow_partial=allow_partial,
                                           bootstrap_draws=bootstrap_draws)
            save_source_evaluation(result, rows, paths["source_dir"])
            loaded["source"] = json.loads(
                (paths["source_dir"] / "source_aggregate.json").read_text(encoding="utf-8"))
            return (f"{result['n_evaluated_images']} images evaluated, "
                    f"{result['n_failed']} failed", result["full_source_holdout_scored"])
        source_ok = run("papila_source_holdout", source)
    else:
        source_ok = False
        step("papila_source_holdout", "skipped", "No frozen model lock")

    # 5–6. External Chákṣu Test (optional input).
    external_ok = False
    if chaksu_test_zip is None:
        step("chaksu_five_reader_preflight", "skipped", "No --chaksu-test-zip given")
        step("chaksu_external_test", "skipped", "No --chaksu-test-zip given")
    else:
        def audit():
            report, failures = check_chaksu_archive(chaksu_test_zip)
            save_chaksu_audit(report, failures, paths["audit_dir"])
            loaded["audit"] = report
            return (f"{report['n_checked']} checked, {report['n_errors']} errors",
                    report["all_published_test_masks_structurally_verified"])
        run("chaksu_five_reader_preflight", audit)
        if ok:
            def external():
                result, rows = run_external_test(chaksu_test_zip, paths["lock"],
                                                 allow_partial=allow_partial)
                save_external(result, rows, paths["external_dir"])
                loaded["external"] = json.loads(
                    (paths["external_dir"] / "external_aggregate.json").read_text(encoding="utf-8"))
                return (f"{result['n_test_images_scored']} scored, {result['n_failed']} failed",
                        not result["partial_or_unverified_external"])
            external_ok = run("chaksu_external_test", external)
        else:
            step("chaksu_external_test", "skipped", "No frozen model lock")

    # 7. Evidence gate needs all six artifacts.
    needed = {"sources.json": paths["sources"], "inventory.json": paths["inventory"],
              "model_lock.json": paths["lock"],
              "source_aggregate.json": paths["source_dir"] / "source_aggregate.json",
              "audit_aggregate.json": paths["audit_dir"] / "audit_aggregate.json",
              "external_aggregate.json": paths["external_dir"] / "external_aggregate.json"}
    absent = [label for label, path in needed.items() if not path.is_file()]
    if absent or not (source_ok and external_ok):
        step("evidence_gate", "skipped", "Missing artifacts: " + (", ".join(absent) or
                                                                  "a required step failed"))
    else:
        def evidence():
            report = review_evidence(
                sources=paths["sources"], papila_inventory=paths["inventory"],
                model_lock=paths["lock"], source_holdout=needed["source_aggregate.json"],
                chaksu_audit=needed["audit_aggregate.json"],
                external_aggregate=needed["external_aggregate.json"])
            save_evidence_review(report, paths["evidence"])
            loaded["evidence"] = report
            return (f"{report['n_passed']}/{report['n_total']} checks passed",
                    report["all_required_artifacts_consistent"])
        run("evidence_gate", evidence)

    evidence = loaded["evidence"]
    manifest["evidence_package_consistent"] = bool(
        evidence and evidence["all_required_artifacts_consistent"])
    manifest["all_executed_steps_passed"] = all(s["status"] != "failed" for s in steps)

    # 8. Aggregate-only HTML report, always written so failures are visible.
    run("html_report", lambda: str(write_html_report(
        paths["report"], pipeline={"steps": list(steps)}, **loaded)))
    manifest["all_executed_steps_passed"] = all(s["status"] != "failed" for s in steps)
    manifest["finished_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    manifest["output_sha256"] = {
        rel: _sha256(out / rel) for rel in AGGREGATE_FILES
        if rel != "pipeline_manifest.json" and (out / rel).is_file()}
    # inventory.json lists per-image entries, so it stays local like *private* files.
    manifest["private_local_files_not_for_sharing"] = sorted(
        p.relative_to(out).as_posix() for p in out.rglob("*")
        if p.is_file() and ("private" in p.name or p.name == "inventory.json"))
    (out / "pipeline_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Run the full HyunOptic research chain into one new folder "
                    "(research only; not clinical validation)")
    p.add_argument("--papila-root", type=Path, required=True,
                   help="Extracted PAPILA folder (contains FundusImages/ and ExpertsSegmentations/)")
    p.add_argument("--chaksu-test-zip", type=Path,
                   help="Original Chaksu Test.zip; omit for a PAPILA-only run")
    p.add_argument("--papila-zip", type=Path,
                   help="Original PAPILA.zip, used only for the archive identity check")
    p.add_argument("--output-dir", type=Path, default=Path("reports/v1"))
    p.add_argument("--allow-partial", action="store_true",
                   help="ONLY for synthetic fixtures or subsets; results are marked unverified")
    p.add_argument("--verify-pixels", action="store_true")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--draws", type=int, default=500)
    p.add_argument("--bootstrap-draws", type=int, default=1000)
    p.add_argument("--strict", action="store_true",
                   help="Exit 2 unless every step ran and the evidence gate is consistent")
    a = p.parse_args(argv)
    try:
        manifest = run_pipeline(
            a.papila_root, a.output_dir, chaksu_test_zip=a.chaksu_test_zip,
            papila_zip=a.papila_zip, allow_partial=a.allow_partial,
            verify_pixels=a.verify_pixels, seed=a.seed, draws=a.draws,
            bootstrap_draws=a.bootstrap_draws)
    except (OSError, ValueError) as exc:
        p.error(str(exc))
    for s in manifest["steps"]:
        print(f"[{s['status']:>10}] {s['name']}: {s['detail']}")
    print(f"Report: {a.output_dir / 'report.html'}")
    print("inventory.json and files named *private* contain per-case data: keep them local.")
    if not manifest["all_executed_steps_passed"]:
        return 1
    if a.strict and not manifest["evidence_package_consistent"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
