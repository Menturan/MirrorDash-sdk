import json
import shutil
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from mirrordash_sdk.cli import main


@pytest.mark.parametrize("template", ["basic", "api"])
def test_a_generated_module_passes_its_own_tests_and_the_validator(template, tmp_path, monkeypatch):
    """What a developer gets from create-module works as it is: its tests pass and it validates."""
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    result = runner.invoke(main, ["create-module", "mirrordash-demo-widget", "--template", template])
    assert result.exit_code == 0, result.output
    module = tmp_path / "mirrordash-demo-widget"

    leftovers = [str(p) for p in module.rglob("*") if p.is_file() and ".git" not in p.parts
                 and "$" in p.read_text(encoding="utf-8", errors="ignore").replace("$schema", "")]
    assert not leftovers, f"unfilled placeholders in {leftovers}"
    assert (module / ".gitignore").is_file()
    assert json.loads((module / "mirrordash_demo_widget" / "config_schema.json").read_text())["title"] == "Demo Widget"

    if not shutil.which("uv"):
        pytest.skip("uv is needed to run the generated module's tests")
    tests = subprocess.run(["uv", "run", "--quiet", "pytest", "-q"], cwd=module, capture_output=True, text=True)
    assert tests.returncode == 0, tests.stdout + tests.stderr

    result = runner.invoke(main, ["validate", str(module)])
    assert result.exit_code == 0, result.output
    # The only thing left to the developer is the screenshot
    warnings = [line for line in result.output.splitlines() if "Warning" in line]
    assert len(warnings) == 1 and "screenshot.png" in warnings[0], result.output


def test_quickstart_creates_sets_up_starts_and_opens(tmp_path, monkeypatch):
    from unittest.mock import patch
    monkeypatch.chdir(tmp_path)
    with patch("mirrordash_sdk.cli.dev_setup_logic") as setup, patch("mirrordash_sdk.cli.open_when_ready") as browser, \
         patch("mirrordash_sdk.cli.start_server_logic") as start:
        result = CliRunner().invoke(main, ["quickstart", "mirrordash-demo"])
    assert result.exit_code == 0, result.output
    module = tmp_path / "mirrordash-demo"
    assert "fetch_json" in (module / "mirrordash_demo" / "plugin.py").read_text()  # the api template by default
    setup.assert_called_once_with(str(module), editable=True)
    browser.assert_called_once()
    start.assert_called_once_with(str(module))


def test_dev_setup_takes_core_from_github_until_the_needed_version_is_on_pypi(tmp_path):
    from unittest.mock import MagicMock, patch
    from mirrordash_sdk.manager import CORE_GIT, CORE_REQUIREMENT, dev_setup_logic
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").touch()

    def run(cmd, **kwargs):
        if kwargs.get("check") and CORE_GIT not in cmd and "install" in cmd:
            raise AssertionError("only the GitHub fallback may be a checked install")
        return MagicMock(returncode=1 if CORE_REQUIREMENT in cmd else 0, stdout="")

    with patch("subprocess.run", side_effect=run) as mock_run:
        dev_setup_logic(str(tmp_path))
    installs = [c.args[0][-1] for c in mock_run.call_args_list if "install" in c.args[0]]
    assert installs == [CORE_REQUIREMENT, CORE_GIT]


def test_validate_warns_about_a_key_shown_in_plain_text(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    runner.invoke(main, ["create-module", "mirrordash-demo", "--template", "api"])
    schema_file = Path("mirrordash-demo/mirrordash_demo/config_schema.json")
    schema = json.loads(schema_file.read_text())
    del schema["properties"]["api_key"]["format"]
    schema_file.write_text(json.dumps(schema))

    result = runner.invoke(main, ["validate", "mirrordash-demo"])
    assert "look secret but show in plain text: ['api_key']" in result.output
