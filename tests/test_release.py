"""`mirrordash-sdk release` in a real Git repository, with a local repository standing in for GitHub."""
import subprocess

import pytest
from click.testing import CliRunner

from mirrordash_sdk.cli import main
from mirrordash_sdk.scaffolder import create_module


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


@pytest.fixture
def module(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for key, value in (("GIT_AUTHOR_NAME", "T"), ("GIT_AUTHOR_EMAIL", "t@t"), ("GIT_COMMITTER_NAME", "T"), ("GIT_COMMITTER_EMAIL", "t@t")):
        monkeypatch.setenv(key, value)
    monkeypatch.setattr("mirrordash_sdk.release.shutil.which", lambda cmd: None if cmd == "gh" else "/usr/bin/" + cmd)
    path = create_module("mirrordash-test", "Test", "T")
    (path / "tests").rename(path / "no-tests")  # the template's tests need the core installed
    git(tmp_path, "init", "--quiet", "--bare", "remote.git")
    git(path, "add", ".")
    git(path, "commit", "--quiet", "-m", "first")
    git(path, "remote", "add", "origin", str(tmp_path / "remote.git"))
    return path


def release(module, *args, answer="y\n"):
    return CliRunner().invoke(main, ["release", *args, "--path", str(module)], input=answer)


def test_dry_run_changes_nothing(module):
    result = release(module, "1.0.0", "--dry-run")
    assert result.exit_code == 0, result.output
    assert "[dry run] set version 0.1.0 -> 1.0.0" in result.output
    assert 'version = "0.1.0"' in (module / "pyproject.toml").read_text()
    assert git(module, "tag") == ""


def test_release_sets_the_version_tags_and_pushes(module):
    result = release(module, "1.0.2")
    assert result.exit_code == 0, result.output
    assert 'version = "1.0.2"' in (module / "pyproject.toml").read_text()
    assert git(module, "ls-remote", "--tags", "origin", "v1.0.2")  # the tag is on the remote
    assert git(module, "log", "-1", "--format=%s") == "Release v1.0.2"
    assert "releases/new?tag=v1.0.2" in result.output  # without gh: a link to finish it

    result = release(module, "1.0.1")  # lower than what is released
    assert result.exit_code != 0 and "choose a higher version" in result.output


def test_stops_on_uncommitted_changes_or_a_bad_version(module):
    assert "isn't a version" in release(module, "1.0").output
    (module / "README.md").write_text("changed")
    result = release(module, "1.0.0")
    assert result.exit_code != 0 and "uncommitted changes" in result.output
