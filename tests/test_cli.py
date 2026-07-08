import json
import os
from pathlib import Path
import sys
from unittest.mock import MagicMock, patch
import pytest
from click.testing import CliRunner

from mirrordash_sdk.cli import main, validate_module, register_module

def test_create_module_dry_run():
    runner = CliRunner()
    result = runner.invoke(main, ["create-module", "mirrordash-test", "--dry-run"])
    assert result.exit_code == 0
    assert "[DRY RUN] Would create module" in result.output
    assert "Would write file" in result.output

def test_create_module_execution():
    runner = CliRunner()
    with runner.isolated_filesystem() as temp_dir:
        result = runner.invoke(main, ["create-module", "mirrordash-test", "--description", "Test desc", "--author", "Tester"])
        assert result.exit_code == 0
        assert "Success! Module bootstrapped successfully." in result.output
        
        module_path = Path("mirrordash-test")
        assert module_path.exists()
        assert (module_path / "pyproject.toml").exists()
        assert (module_path / "mirrordash_test" / "plugin.py").exists()
        assert (module_path / "mirrordash_test" / "config_schema.json").exists()
        assert (module_path / "mirrordash_test" / "icon.svg").exists()
        assert (module_path / "mirrordash_test" / "translations" / "en.json").exists()
        assert (module_path / "mirrordash_test" / "templates" / "widget.html").exists()
        assert (module_path / "tests" / "test_plugin.py").exists()
        assert (module_path / "README.md").exists()

        # Check default icon.svg
        icon_text = (module_path / "mirrordash_test" / "icon.svg").read_text()
        assert "<svg" in icon_text

        # Check config_schema has no custom icon field by default
        with open(module_path / "mirrordash_test" / "config_schema.json") as f:
            schema_data = json.load(f)
            assert "icon" not in schema_data


def test_create_module_custom_fa_icon():
    runner = CliRunner()
    with runner.isolated_filesystem() as temp_dir:
        result = runner.invoke(main, ["create-module", "mirrordash-test", "--icon", "fa-bolt"])
        assert result.exit_code == 0
        
        module_path = Path("mirrordash-test")
        assert (module_path / "mirrordash_test" / "config_schema.json").exists()
        assert not (module_path / "mirrordash_test" / "icon.svg").exists()

        # Check config_schema has custom icon field
        with open(module_path / "mirrordash_test" / "config_schema.json") as f:
            schema_data = json.load(f)
            assert schema_data.get("icon") == "fa-bolt"

def test_validate_invalid_path():
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["validate", "."])
        assert result.exit_code != 0
        assert "pyproject.toml not found" in result.output

def test_validate_valid_module():
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["create-module", "mirrordash-test"])
        result = runner.invoke(main, ["validate", "mirrordash-test"])
        assert result.exit_code == 0
        assert "STATUS: PASS WITH WARNINGS" in result.output

@patch("subprocess.run")
def test_register_module(mock_run):
    res = MagicMock()
    res.returncode = 0
    mock_run.return_value = res
    
    runner = CliRunner()
    with runner.isolated_filesystem() as temp_dir:
        runner.invoke(main, ["create-module", "mirrordash-test"])
        
        config_file = Path(temp_dir) / "config.json"
        
        with patch.dict(os.environ, {"MIRRORDASH_CONFIG_PATH": str(config_file)}):
            result = runner.invoke(main, ["register", "mirrordash-test"])
            
            assert result.exit_code == 0
            mock_run.assert_called()
            
            assert config_file.exists()
            with open(config_file, "r") as f:
                config_data = json.load(f)
            assert "modules" in config_data
            assert "mirrordash_test" in config_data["modules"]
            assert config_data["modules"]["mirrordash_test"]["enabled"] is True

def run_side_effect(*args, **kwargs):
    # If it's creating venv, create the dummy python executable
    cmd = args[0]
    if len(cmd) > 2 and ("venv" in cmd or "-m" in cmd and "venv" in cmd):
        venv_dir = Path(cmd[-1])
        venv_bin = venv_dir / ("Scripts" if os.name == "nt" else "bin")
        venv_bin.mkdir(parents=True, exist_ok=True)
        venv_python = venv_bin / ("python.exe" if os.name == "nt" else "python")
        venv_python.touch()
    
    res = MagicMock()
    res.returncode = 0
    return res

@patch("subprocess.run")
def test_dev_setup(mock_run):
    mock_run.side_effect = run_side_effect
    
    runner = CliRunner()
    with runner.isolated_filesystem() as temp_dir:
        result = runner.invoke(main, ["dev-setup", "--path", "."])
        assert result.exit_code == 0
        assert "Setting up developer environment at" in result.output
        assert "Success! Development environment is set up." in result.output
        mock_run.assert_called()

@patch("subprocess.run")
def test_dev_setup_with_editable(mock_run):
    mock_run.side_effect = run_side_effect
    
    runner = CliRunner()
    with runner.isolated_filesystem() as temp_dir:
        runner.invoke(main, ["create-module", "mirrordash-test"])
        
        config_file = Path(temp_dir) / "config.json"
        
        with patch.dict(os.environ, {"MIRRORDASH_CONFIG_PATH": str(config_file)}):
            result = runner.invoke(main, ["dev-setup", "--path", "mirrordash-test", "--editable"])
            assert result.exit_code == 0
            assert "Registering module..." in result.output

@patch("subprocess.run")
def test_start_server_venv(mock_run):
    res = MagicMock()
    res.returncode = 0
    mock_run.return_value = res
    
    runner = CliRunner()
    with runner.isolated_filesystem() as temp_dir:
        venv_bin = Path(temp_dir) / ".venv" / ("Scripts" if os.name == "nt" else "bin")
        venv_bin.mkdir(parents=True, exist_ok=True)
        venv_python = venv_bin / ("python.exe" if os.name == "nt" else "python")
        venv_python.touch()
        
        result = runner.invoke(main, ["start", "--path", "."])
        assert result.exit_code == 0
        assert "Starting MirrorDash server using virtual environment python" in result.output
        mock_run.assert_called_with([str(venv_python), "-m", "mirrordash_core.main"])

@patch("subprocess.run")
def test_start_server_no_venv(mock_run):
    res = MagicMock()
    res.returncode = 0
    mock_run.return_value = res
    
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["start", "--path", "."])
        assert result.exit_code == 0
        assert "Warning: No local virtual environment (.venv) found" in result.output
        mock_run.assert_called_with(["python", "-m", "mirrordash_core.main"])

@patch("subprocess.run", side_effect=KeyboardInterrupt)
def test_start_server_interrupt(mock_run):
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(main, ["start", "--path", "."])
        assert result.exit_code == 0
        assert "MirrorDash server stopped." in result.output

@patch("subprocess.run")
def test_build_command(mock_run):
    res = MagicMock()
    res.returncode = 0
    mock_run.return_value = res
    
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["create-module", "mirrordash-test"])
        
        result = runner.invoke(main, ["build", "--path", "mirrordash-test"])
        assert result.exit_code == 0
        assert "Building package at" in result.output
        mock_run.assert_called()

@patch("subprocess.run")
def test_publish_command_success(mock_run):
    res = MagicMock()
    res.returncode = 0
    mock_run.return_value = res
    
    runner = CliRunner()
    with runner.isolated_filesystem():
        runner.invoke(main, ["create-module", "mirrordash-test"])
        
        dist_dir = Path("mirrordash-test") / "dist"
        dist_dir.mkdir(exist_ok=True)
        (dist_dir / "mirrordash_test-0.1.0-py3-none-any.whl").touch()
        
        result = runner.invoke(main, ["publish", "--path", "mirrordash-test", "--force"])
        assert result.exit_code == 0
        assert "Publishing package at" in result.output
        mock_run.assert_called()
