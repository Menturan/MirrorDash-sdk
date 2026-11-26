"""`mirrordash-sdk release`: give a module a new version that mirrors can install.

Mirrors offer a module's newest GitHub Release, and show the version in its pyproject.toml. This
sets both from one number, so they never differ: version in pyproject.toml, commit, tag vX.Y.Z,
push, the GitHub Release and the `mirrordash-module` topic on the repository, which mirrors search for
(with the `gh` tool, or what to do by hand).

A version like 1.10.0rc1 (a1, b1, rc1) is a test version: it becomes a GitHub pre-release, which mirrors
only offer when the owner switches on "Test versions" in that module's settings. Versions are compared
as PEP 440 does (1.10.0rc1 < 1.10.0), with a small parser here so the SDK needs no extra dependency.
"""
import re
import shutil
import subprocess
from pathlib import Path

import click

from .validator import validate_module

VERSION_LINE = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)
TOPIC = "mirrordash-module"
BY_HAND = f"On the repository page, About -> Topics, add '{TOPIC}' (mirrors only list repositories named mirrordash-* with it)."


class Stop(click.ClickException):
    def format_message(self):
        return f"Stopped: {self.message}"


VERSION = re.compile(r"v?(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?")
STAGES = {"a": 0, "b": 1, "rc": 2}


def parse(version: str) -> tuple[int, int, int, int, int]:
    """A sortable key in PEP 440 order: X.Y.ZaN < X.Y.ZbN < X.Y.ZrcN < X.Y.Z."""
    match = VERSION.fullmatch(version)
    if not match:
        raise Stop(f"'{version}' isn't a version like 1.2.3 or a test version like 1.2.3rc1 (a1, b1 or rc1).")
    major, minor, patch, stage, number = match.groups()
    return int(major), int(minor), int(patch), STAGES.get(stage, 3), int(number or 0)


def is_prerelease(version: str) -> bool:
    return parse(version)[3] < 3


def release_module(path: Path, version: str | None, dry_run: bool = False) -> None:
    root = path.resolve()

    def run(*cmd, change=False, check=True):
        """Run a command in the module's folder and return its output. change=True: skipped in a dry run."""
        if change and dry_run:
            click.echo(f"  [dry run] {' '.join(cmd)}")
            return ""
        result = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        if check and result.returncode != 0:
            raise Stop(f"`{' '.join(cmd)}` failed:\n{result.stdout}{result.stderr}")
        return result.stdout.strip()

    # 1. A module in a Git repository with a GitHub remote, everything committed
    pyproject = root / "pyproject.toml"
    if not pyproject.exists() or not VERSION_LINE.search(pyproject.read_text()):
        raise Stop(f"no pyproject.toml with a version line in {root}.")
    if not shutil.which("git") or run("git", "rev-parse", "--is-inside-work-tree", check=False) != "true":
        raise Stop("this folder isn't a Git repository. See 'Sharing your module' in the module guide.")
    remote = run("git", "remote", "get-url", "origin", check=False)
    if not remote:
        raise Stop("the repository isn't on GitHub yet (no remote called origin). See 'Sharing your module' in the module guide.")
    if run("git", "status", "--porcelain"):
        raise Stop("there are uncommitted changes; commit or remove them first.")

    # 2. The version: higher than now, or the current one if it was never released
    current = VERSION_LINE.search(pyproject.read_text()).group(1)
    now = parse(current)

    def tagged(v):
        return bool(run("git", "tag", "--list", f"v{v}") or run("git", "ls-remote", "--tags", "origin", f"v{v}", check=False))

    if not tagged(current):
        suggestion = current
    elif is_prerelease(current):
        suggestion = f"{now[0]}.{now[1]}.{now[2]}"  # the final version of that test version
    else:
        suggestion = f"{now[0]}.{now[1]}.{now[2] + 1}"
    version = (version or click.prompt(f"Current version {current}. Release version", default=suggestion)).lstrip("v")
    new = parse(version)
    if new < now or tagged(version):
        raise Stop(f"{version} is already released or lower than {current}; choose a higher version.")
    tag = f"v{version}"
    test_version = is_prerelease(version)

    # 3. Check the module and run its tests before anything changes
    if not validate_module(str(root), exit_on_fail=False):
        raise Stop("the module has errors (see above); fix them first.")
    if (root / "tests").is_dir():
        click.echo("Running the tests...")
        if subprocess.run(["uv", "run", "--quiet", "pytest", "-q"], cwd=root).returncode != 0:
            raise Stop("the tests failed.")
    question = (
        f"Release {tag} as a test version (pre-release)? Only mirrors with Test versions on for this module are offered it."
        if test_version else f"Release {tag}?"
    )
    if not dry_run and not click.confirm(question, default=False):
        raise Stop("nothing was changed.")

    # 4. Version, commit, push, tag, release
    if version != current:
        if dry_run:
            click.echo(f"  [dry run] set version {current} -> {version} in pyproject.toml")
        else:
            pyproject.write_text(VERSION_LINE.sub(f'version = "{version}"', pyproject.read_text(), count=1))
            if (root / "uv.lock").exists():
                run("uv", "lock", "--quiet")
        run("git", "add", "pyproject.toml", *(["uv.lock"] if (root / "uv.lock").exists() else []), change=True)
        run("git", "commit", "-m", f"Release {tag}", change=True)
    run("git", "push", "origin", "HEAD", change=True)
    run("git", "tag", "-a", tag, "-m", tag, change=True)
    run("git", "push", "origin", tag, change=True)

    repo_url = re.sub(r"\.git$", "", remote.replace("git@github.com:", "https://github.com/"))
    if dry_run:
        click.echo(f"\nDry run: nothing was changed. Without --dry-run this releases {tag}{' as a test version (pre-release)' if test_version else ''}.")
    elif shutil.which("gh"):
        run("gh", "release", "create", tag, "--title", tag, "--generate-notes", *(["--prerelease"] if test_version else []), change=True)
        if test_version:
            click.echo(f"\n{tag} is released as a test version. Mirrors with Test versions on for this module offer it.")
        else:
            click.echo(f"\n{tag} is released. Mirrors offer it as an update on the module's card.")
        try:  # idempotent; the release is out already, so a failure here only asks for the step by hand
            run("gh", "repo", "edit", "--add-topic", TOPIC, change=True)
        except Stop:
            click.echo(f"The topic '{TOPIC}' couldn't be set. {BY_HAND}")
    else:
        click.echo(f"\n{tag} is pushed. Last step, the GitHub Release (mirrors only see releases):")
        click.echo(f"  open {repo_url}/releases/new?tag={tag} and press 'Publish release'"
                   + (", after ticking 'Set as a pre-release' (it is a test version)." if test_version else "."))
        click.echo(f"And the topic mirrors search for: {BY_HAND}")
