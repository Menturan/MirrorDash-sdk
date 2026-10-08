#!/usr/bin/env python3
"""Release a new mirrordash-sdk version to PyPI.

    python3 scripts/release.py            # asks for the version, then releases
    python3 scripts/release.py 0.2.1      # releases 0.2.1
    python3 scripts/release.py --dry-run  # shows what it would do, changes nothing

It checks that master is clean and equal to origin/master and that the tests pass, sets the
version in pyproject.toml (and uv.lock), commits, pushes master and pushes the tag vX.Y.Z.
GitHub Actions (.github/workflows/publish.yml) then tests, builds and publishes it to PyPI.
Needs git and uv. Standard library only.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = ROOT / "pyproject.toml"
VERSION_LINE = re.compile(r'^version = "([^"]+)"$', re.MULTILINE)
DRY_RUN = "--dry-run" in sys.argv


def die(message):
    sys.exit(f"Stopped: {message}")


def run(*cmd, change=False):
    """Run a command in the repo and return its output. With change=True it is skipped in a dry run."""
    if change and DRY_RUN:
        print(f"  [dry run] {' '.join(cmd)}")
        return ""
    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        die(f"`{' '.join(cmd)}` failed:\n{result.stdout}{result.stderr}")
    return result.stdout.strip()


def parse(version):
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)", version)
    if not match:
        die(f"'{version}' isn't a version like 1.2.3.")
    return tuple(int(n) for n in match.groups())


def main():
    current = VERSION_LINE.search(PYPROJECT.read_text()).group(1)
    major, minor, patch = parse(current)

    # 1. Only release what is on GitHub's master, so the tag points at code others can see
    if run("git", "branch", "--show-current") != "master":
        die("switch to master first.")
    if run("git", "status", "--porcelain"):
        die("there are uncommitted changes; commit or remove them first.")
    run("git", "fetch", "--quiet", "origin")
    if run("git", "rev-parse", "HEAD") != run("git", "rev-parse", "origin/master"):
        die("master isn't the same as origin/master; pull or push first.")

    # 2. The new version: given, or asked for. The version in pyproject.toml can be released as it
    # is once (no tag for it yet); after that, the next patch version is suggested.
    def tagged(v):
        return bool(run("git", "tag", "--list", f"v{v}") or run("git", "ls-remote", "--tags", "origin", f"v{v}"))

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    suggestion = current if not tagged(current) else f"{major}.{minor}.{patch + 1}"
    version = args[0] if args else (input(f"Current version {current}. Release version [{suggestion}]: ").strip() or suggestion)
    if parse(version) < (major, minor, patch) or (version == current and tagged(current)):
        die(f"{version} is already released or lower than {current}; choose a higher version.")
    tag = f"v{version}"
    if tagged(version):
        die(f"the tag {tag} already exists.")

    # 3. The tests must pass before anything changes
    print("Running the tests...")
    if subprocess.run(["uv", "run", "--quiet", "pytest", "-q"], cwd=ROOT).returncode != 0:
        die("the tests failed.")

    if not DRY_RUN and input(f"Release {tag} to PyPI? [y/N] ").strip().lower() != "y":
        die("nothing was changed.")

    # 4. Version, commit, push, tag: pushing the tag starts publish.yml
    if version != current:
        if DRY_RUN:
            print(f"  [dry run] set version {current} -> {version} in pyproject.toml and uv.lock")
        else:
            PYPROJECT.write_text(VERSION_LINE.sub(f'version = "{version}"', PYPROJECT.read_text(), count=1))
            run("uv", "lock", "--quiet")
        run("git", "add", "pyproject.toml", "uv.lock", change=True)
        run("git", "commit", "-m", f"chore: release {tag}", change=True)
        run("git", "push", "origin", "master", change=True)
    run("git", "tag", "-a", tag, "-m", tag, change=True)
    run("git", "push", "origin", tag, change=True)

    print(f"\n{tag} is pushed. GitHub Actions now tests, builds and publishes it (a few minutes):")
    print("  https://github.com/Menturan/MirrorDash-sdk/actions")
    print(f"  then: https://pypi.org/project/mirrordash-sdk/{version}/")


if __name__ == "__main__":
    main()
