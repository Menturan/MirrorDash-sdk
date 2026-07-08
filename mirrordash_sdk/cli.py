import click
from pathlib import Path

from .scaffolder import create_module
from .validator import validate_module
from .manager import (
    register_module,
    dev_setup_logic,
    start_server_logic,
    build_module_logic,
    publish_module_logic,
)

@click.group()
def main():
    """MirrorDash developer CLI and tools."""
    pass

@main.command("create-module")
@click.argument("name")
@click.option("--description", "-d", default="A custom module for MirrorDash", help="Module description")
@click.option("--author", "-a", default="MirrorDash Developer", help="Module author name")
@click.option("--icon", "-i", default=None, help="FontAwesome class OR path to a custom SVG file")
@click.option("--dry-run", is_flag=True, help="Preview generated files without creating them")
def create_module_cmd(name, description, author, icon, dry_run):
    """Bootstrap a new custom module."""
    create_module(name, description, author, icon, dry_run)

@main.command("validate")
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False, path_type=Path))
def validate_cmd(path):
    """Validate a module's structure and conformity."""
    validate_module(str(path))

@main.command("register")
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False, path_type=Path))
def register_cmd(path):
    """Install module in editable mode and register in config.json."""
    register_module(str(path))

@main.command("dev-setup")
@click.option("--path", "-p", default=".", type=click.Path(file_okay=False, path_type=Path), help="Target directory for the environment (default: .)")
@click.option("--core-git", help="Install MirrorDash core from a specific Git URL instead of PyPI")
@click.option("--editable", "-e", is_flag=True, help="Automatically install and register the module in editable mode after setup")
def dev_setup_cmd(path: Path, core_git: str, editable: bool):
    """Set up a local development environment (venv + core installation)."""
    dev_setup_logic(str(path), core_git, editable)

@main.command("start")
@click.option("--path", "-p", default=".", type=click.Path(file_okay=False, path_type=Path), help="Project or environment root (default: .)")
def start_cmd(path: Path):
    """Start the MirrorDash application."""
    start_server_logic(str(path))

@main.command("build")
@click.option("--path", "-p", default=".", type=click.Path(exists=True, file_okay=False, path_type=Path), help="Path to module directory (default: .)")
def build_cmd(path: Path):
    """Build the module distribution package (wheel & sdist)."""
    build_module_logic(str(path))

@main.command("publish")
@click.option("--path", "-p", default=".", type=click.Path(exists=True, file_okay=False, path_type=Path), help="Path to module directory (default: .)")
@click.option("--force", "-f", is_flag=True, help="Force publish even if validation fails")
def publish_cmd(path: Path, force: bool):
    """Validate and publish the module to PyPI."""
    publish_module_logic(str(path), force)

if __name__ == "__main__":
    main()
