import json
import os
import re
import shutil
import subprocess
import sys
from importlib.resources import files
from pathlib import Path
from string import Template

TEMPLATES = ("basic", "api")
TEMPLATES_DIR = files("mirrordash_sdk") / "templates"


def _template_files(template: str):
    """(relative path, text) for every file of the template, the shared files first."""
    for part in ("common", template):
        root = Path(str(TEMPLATES_DIR / part))
        for file in sorted(root.rglob("*")):
            if file.is_file() and "__pycache__" not in file.parts:
                yield file.relative_to(root), file.read_text(encoding="utf-8")


def create_module(name: str, description: str, author: str, icon: str = None, dry_run: bool = False,
                  template: str = "basic") -> Path:
    """Write a new module from a template (mirrordash_sdk/templates/<template>) and return its directory.

    Files use $folder_name, $package_name, $class_name, $title, $description and $author; a
    directory named __package__ becomes the Python package, and gitignore becomes .gitignore.
    """
    folder_name = name.lower().replace("_", "-")  # the distribution name: mirrordash-my-widget
    package_name = name.lower().replace("-", "_")  # the import name: mirrordash_my_widget
    clean_name = package_name.replace("mirrordash_", "")
    class_name = "".join(word.capitalize() for word in clean_name.split("_")) + "Module"
    title = clean_name.replace("_", " ").title()

    if not re.match(r"^[a-z0-9\-]+$", folder_name):
        print(f"Error: Invalid module name '{name}'. Only letters, digits, hyphens and underscores are allowed.", file=sys.stderr)
        sys.exit(1)
    if template not in TEMPLATES:
        print(f"Error: Unknown template '{template}'. Choose one of: {', '.join(TEMPLATES)}.", file=sys.stderr)
        sys.exit(1)
    if not folder_name.startswith("mirrordash-"):
        print(f"Warning: Module name '{name}' does not start with 'mirrordash-'. "
              f"Use the prefix (e.g. mirrordash-{clean_name}) so modules are easy to find and don't clash.")

    # Inside a checkout with a modules/ directory, the module goes there
    modules_dir = Path.cwd() / "modules"
    target_dir = (modules_dir if modules_dir.is_dir() else Path.cwd()) / folder_name
    if not dry_run and target_dir.exists():
        print(f"Error: Directory '{target_dir}' already exists.", file=sys.stderr)
        sys.exit(1)

    custom_svg = fa_icon = None
    if icon and icon.lower().endswith(".svg"):
        if not Path(icon).is_file():
            print(f"Error: Custom SVG icon file '{icon}' not found.", file=sys.stderr)
            sys.exit(1)
        custom_svg = Path(icon).read_text(encoding="utf-8").strip() + "\n"
    elif icon:
        fa_icon = icon

    values = {"folder_name": folder_name, "package_name": package_name, "class_name": class_name,
              "title": title, "description": description, "author": author}
    print(f"{'[DRY RUN] Would create' if dry_run else 'Creating'} module '{folder_name}' "
          f"from the '{template}' template in {target_dir}...")

    for relative, text in _template_files(template):
        relative = Path(*(package_name if part == "__package__" else ".gitignore" if part == "gitignore" else part
                          for part in relative.parts))
        if relative.name == "icon.svg":
            if fa_icon:
                continue  # the icon is a FontAwesome class in config_schema.json instead
            text = custom_svg or text
        else:
            text = Template(text).safe_substitute(values)
        if relative.name == "config_schema.json" and fa_icon:
            schema = json.loads(text)
            text = json.dumps({"title": schema.pop("title"), "icon": fa_icon, **schema}, indent=2) + "\n"

        destination = target_dir / relative
        if dry_run:
            print(f"\n[DRY RUN] Would write file: {destination} with content:\n{text.strip()}")
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")

    if dry_run:
        print("\n[DRY RUN] Would run: git init")
        print("\nDry run completed. No files were written.")
        return target_dir

    # Only a repository, no commit: a first commit needs the user's name set in git (the guide's part 11)
    if shutil.which("git"):
        if subprocess.run(["git", "init", "--quiet"], cwd=target_dir).returncode == 0:
            print("Git repository initialized.")
    else:
        print("Warning: 'git' command not found. Skipping Git repository initialization.")

    rel_path = os.path.relpath(target_dir)
    print("\nSuccess! Module bootstrapped successfully.")
    print("Next steps:")
    print(f"  cd {rel_path}")
    print("  uv run pytest                  # the module's tests")
    print("  uvx mirrordash-sdk dev-setup -e  # a local mirror with this module on it")
    print("  uvx mirrordash-sdk start         # then open http://localhost:8000/")
    return target_dir
