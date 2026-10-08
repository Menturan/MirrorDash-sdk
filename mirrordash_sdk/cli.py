import click
from pathlib import Path

from .scaffolder import TEMPLATES, create_module
from .validator import validate_module
from .release import release_module
from .manager import (
    register_module,
    dev_setup_logic,
    open_when_ready,
    start_server_logic,
)

TEMPLATE_HELP = "basic: a module that shows something it works out itself; api: fetches data from an API with an API key"

@click.group()
def main():
    """MirrorDash developer CLI and tools."""
    pass

@main.command("quickstart")
@click.argument("name")
@click.option("--template", "-t", type=click.Choice(TEMPLATES), default="api", show_default=True, help=TEMPLATE_HELP)
@click.option("--description", "-d", default="A custom module for MirrorDash", help="Module description")
@click.option("--author", "-a", default="MirrorDash Developer", help="Module author name")
def quickstart_cmd(name, template, description, author):
    """Create a module, set up a local mirror with it, start it and open it in the browser."""
    target = create_module(name, description, author, template=template)
    dev_setup_logic(str(target), editable=True)
    print("\nStarting the mirror; the browser opens when it's up. Stop it with Ctrl+C.")
    open_when_ready()
    start_server_logic(str(target))

@main.command("create-module")
@click.argument("name")
@click.option("--template", "-t", type=click.Choice(TEMPLATES), default="basic", show_default=True, help=TEMPLATE_HELP)
@click.option("--description", "-d", default="A custom module for MirrorDash", help="Module description")
@click.option("--author", "-a", default="MirrorDash Developer", help="Module author name")
@click.option("--icon", "-i", default=None, help="FontAwesome class OR path to a custom SVG file")
@click.option("--dry-run", is_flag=True, help="Preview generated files without creating them")
def create_module_cmd(name, template, description, author, icon, dry_run):
    """Bootstrap a new custom module."""
    create_module(name, description, author, icon, dry_run, template=template)

@main.command("validate")
@click.argument("path", default=".", type=click.Path(exists=True, file_okay=False, path_type=Path))
def validate_cmd(path):
    """Validate a module's structure and conformity."""
    validate_module(str(path))

@main.command("release")
@click.argument("version", required=False)
@click.option("--path", "-p", default=".", type=click.Path(exists=True, file_okay=False, path_type=Path), help="The module's folder (default: .)")
@click.option("--dry-run", is_flag=True, help="Show what it would do, change nothing")
def release_cmd(version, path, dry_run):
    """Release a new version of the module, e.g. `release 1.0.2`: sets it in pyproject.toml, tags it,
    pushes and makes the GitHub Release that mirrors install from."""
    release_module(path, version, dry_run)

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

if __name__ == "__main__":
    main()
