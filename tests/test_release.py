"""`mirrordash-sdk release` in a real Git repository, with a local repository standing in for GitHub."""
import subprocess

import pytest
from click.testing import CliRunner

from mirrordash_sdk.cli import main
from mirrordash_sdk.release import Stop, parse
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
    assert "nothing was changed" in result.output and "is pushed" not in result.output
    assert 'version = "0.1.0"' in (module / "pyproject.toml").read_text()
    assert git(module, "tag") == ""


def test_release_sets_the_version_tags_and_pushes(module):
    result = release(module, "1.0.2")
    assert result.exit_code == 0, result.output
    assert 'version = "1.0.2"' in (module / "pyproject.toml").read_text()
    assert git(module, "ls-remote", "--tags", "origin", "v1.0.2")  # the tag is on the remote
    assert git(module, "log", "-1", "--format=%s") == "Release v1.0.2"
    assert "releases/new?tag=v1.0.2" in result.output  # without gh: a link to finish it
    assert "Topics" in result.output and "mirrordash-module" in result.output  # and the topic by hand

    result = release(module, "1.0.1")  # lower than what is released
    assert result.exit_code != 0 and "choose a higher version" in result.output


def test_stops_on_uncommitted_changes_or_a_bad_version(module):
    assert "isn't a version" in release(module, "1.0").output
    (module / "README.md").write_text("changed")
    result = release(module, "1.0.0")
    assert result.exit_code != 0 and "uncommitted changes" in result.output


def test_release_with_gh_creates_the_release_and_sets_the_topic(module, monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        if cmd[0] == "gh":
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 1 if cmd[:2] == ("gh", "repo") and fail else 0, "", "no")
        return real_run(cmd, **kwargs)

    real_run, fail = subprocess.run, False
    monkeypatch.setattr("mirrordash_sdk.release.shutil.which", lambda cmd: "/usr/bin/" + cmd)
    monkeypatch.setattr("mirrordash_sdk.release.subprocess.run", fake_run)
    result = release(module, "1.0.0")
    assert result.exit_code == 0, result.output
    assert ("gh", "repo", "edit", "--add-topic", "mirrordash-module") in calls

    fail = True  # a failing topic doesn't undo the release: it says what to do by hand
    result = release(module, "1.0.1")
    assert result.exit_code == 0 and "is released" in result.output and "Topics" in result.output


@pytest.mark.parametrize("version", ["1.2.3", "v1.2.3", "1.10.0rc1", "v1.0.0a2", "1.0.0b10"])
def test_parse_accepts_plain_and_pep440_pre_releases(version):
    parse(version)


@pytest.mark.parametrize("version", ["1.0", "1.0.0rc", "1.0.0-rc1", "1.0.0.rc1", "1.0.0c1", "1.0.0dev1", "1.0.0rc1.post1", "x"])
def test_parse_rejects_other_versions(version):
    with pytest.raises(Stop):
        parse(version)


def test_parse_orders_like_pep440():
    ordered = ["1.9.0", "1.10.0a1", "1.10.0b1", "1.10.0rc1", "1.10.0rc2", "1.10.0", "1.10.1"]
    assert [parse(v) for v in ordered] == sorted(parse(v) for v in ordered)
    assert parse("v1.10.0rc1") == parse("1.10.0rc1") > parse("1.9.0")


def test_dry_run_of_a_test_version_says_so(module):
    result = release(module, "1.0.0rc1", "--dry-run")
    assert result.exit_code == 0, result.output
    assert "[dry run] set version 0.1.0 -> 1.0.0rc1" in result.output
    assert "releases v1.0.0rc1 as a test version (pre-release)" in result.output
    assert git(module, "tag") == ""


def test_test_version_by_hand_and_ordering(module):
    result = release(module, "1.0.0rc1", answer="n\n")
    assert "Release v1.0.0rc1 as a test version (pre-release)? Only mirrors with Test versions on" in result.output
    assert result.exit_code != 0 and git(module, "tag") == ""

    result = release(module, "1.0.0rc1")
    assert result.exit_code == 0, result.output
    assert 'version = "1.0.0rc1"' in (module / "pyproject.toml").read_text()
    assert git(module, "tag") == "v1.0.0rc1"
    assert "Set as a pre-release" in result.output

    assert release(module, "1.0.0rc2").exit_code == 0  # later test version
    assert release(module, "1.0.0").exit_code == 0  # final after its test versions
    result = release(module, "1.0.0rc3")  # a test version after the final is refused
    assert result.exit_code != 0 and "choose a higher version" in result.output


@pytest.mark.parametrize("version, prerelease", [("1.0.0rc1", True), ("1.0.0", False)])
def test_gh_gets_prerelease_only_for_test_versions(module, monkeypatch, version, prerelease):
    calls = []
    real_run = subprocess.run

    def fake_run(cmd, **kwargs):
        if cmd[0] == "gh":
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, "", "")
        return real_run(cmd, **kwargs)

    monkeypatch.setattr("mirrordash_sdk.release.shutil.which", lambda cmd: "/usr/bin/" + cmd)
    monkeypatch.setattr("mirrordash_sdk.release.subprocess.run", fake_run)
    result = release(module, version)
    assert result.exit_code == 0, result.output
    create = next(c for c in calls if c[:3] == ("gh", "release", "create"))
    assert ("--prerelease" in create) is prerelease
    assert ("is released as a test version. Mirrors with Test versions on for this module offer it." in result.output) is prerelease
