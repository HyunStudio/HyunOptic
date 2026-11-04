"""Source identity cannot come from a caller's repository or CI environment."""
import importlib
import subprocess

import pytest

from hyunoptic.pipeline import _git_commit


def test_pipeline_missing_git_does_not_trust_github_sha(monkeypatch):
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)

    def missing(*args, **kwargs):
        raise FileNotFoundError("git is not installed")

    monkeypatch.setattr(subprocess, "check_output", missing)
    assert _git_commit() == "unknown"


def test_reproduce_missing_git_keeps_version_and_unknown_commit(tmp_path, monkeypatch):
    from hyunoptic.repro import reproduce
    from test_repro import make_fake_papila

    monkeypatch.setenv("GITHUB_SHA", "unbound CI commit")

    def missing(*args, **kwargs):
        raise FileNotFoundError("git is not installed")

    monkeypatch.setattr(subprocess, "check_output", missing)
    result = reproduce(make_fake_papila(tmp_path), tmp_path / "out",
                       allow_partial=True, draws=30, bootstrap_draws=100)
    assert result["source_code_git_commit_if_available"] == "unknown"
    assert result["version"]


def provenance():
    return importlib.import_module("hyunoptic.provenance")


@pytest.fixture
def source_checkout(tmp_path, monkeypatch):
    root = tmp_path / "app"
    package = root / "src" / "hyunoptic"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (root / "pyproject.toml").write_text('[project]\nname = "hyunoptic"\n')
    # Worktrees use a file rather than a directory here.
    (root / ".git").write_text("gitdir: ../main/.git/worktrees/app\n")
    monkeypatch.setattr(provenance(), "__file__", str(package / "provenance.py"))
    return root


def git_output(monkeypatch, root, head="0123456789abcdef" * 2 + "01234567", *, top=None):
    def output(command, **kwargs):
        assert command[:3] == ["git", "-C", str(root)]
        assert 0 < kwargs["timeout"] <= 5
        assert not any(key.startswith("GIT_") for key in kwargs["env"])
        if command[3:] == ["rev-parse", "--show-toplevel"]:
            return str(root if top is None else top) + "\n"
        assert command[3:] == ["rev-parse", "--verify", "HEAD^{commit}"]
        return head + "\n"

    monkeypatch.setattr(subprocess, "check_output", output)


def test_source_uses_own_checkout_with_unrelated_cwd_and_git_environment(source_checkout, tmp_path, monkeypatch):
    caller = tmp_path / "unrelated"
    caller.mkdir()
    (caller / ".git").mkdir()
    monkeypatch.chdir(caller)
    monkeypatch.setenv("GIT_DIR", str(caller / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(caller))
    monkeypatch.setenv("GITHUB_SHA", "bogus CI value")
    git_output(monkeypatch, source_checkout)
    assert provenance().source_commit() == "0123456789abcdef0123456789abcdef01234567"


@pytest.mark.parametrize("error", [
    FileNotFoundError("git"),
    subprocess.TimeoutExpired("git", 5),
    subprocess.CalledProcessError(128, "git"),
])
def test_git_failures_return_unknown(source_checkout, monkeypatch, error):
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)

    def failing(*args, **kwargs):
        raise error

    monkeypatch.setattr(subprocess, "check_output", failing)
    assert provenance().source_commit() == "unknown"


@pytest.mark.parametrize("head", ["", "HEAD", "abc123", "z" * 40, "a" * 41, "a" * 40 + "\nother"])
def test_invalid_git_hash_is_unknown(source_checkout, monkeypatch, head):
    git_output(monkeypatch, source_checkout, head)
    assert provenance().source_commit() == "unknown"


def test_parent_repository_cannot_supply_commit(source_checkout, monkeypatch):
    git_output(monkeypatch, source_checkout, top=source_checkout.parent)
    assert provenance().source_commit() == "unknown"


@pytest.mark.parametrize("top", ["", "."])
def test_invalid_git_toplevel_cannot_resolve_through_cwd(source_checkout, monkeypatch, top):
    monkeypatch.chdir(source_checkout)
    git_output(monkeypatch, source_checkout, top=top)
    assert provenance().source_commit() == "unknown"


def test_source_copy_without_git_is_unknown_even_inside_another_repo(source_checkout, monkeypatch):
    (source_checkout / ".git").unlink()
    (source_checkout.parent / ".git").mkdir()
    git_output(monkeypatch, source_checkout, top=source_checkout.parent)
    assert provenance().source_commit() == "unknown"


def test_installed_wheel_does_not_inherit_enclosing_repository(tmp_path, monkeypatch):
    package = tmp_path / "repo" / ".venv" / "Lib" / "site-packages" / "hyunoptic"
    package.mkdir(parents=True)
    (tmp_path / "repo" / ".git").mkdir()
    monkeypatch.setattr(provenance(), "__file__", str(package / "provenance.py"))
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    assert provenance().source_commit() == "unknown"


def test_worktree_and_sha256_git_hash_are_supported(source_checkout, monkeypatch):
    git_output(monkeypatch, source_checkout, "a" * 64)
    assert provenance().source_commit() == "a" * 64


def test_unrelated_project_markers_do_not_identify_application(source_checkout, monkeypatch):
    (source_checkout / "pyproject.toml").write_text('[project]\nname = "other-project"\n')
    git_output(monkeypatch, source_checkout)
    assert provenance().source_commit() == "unknown"
