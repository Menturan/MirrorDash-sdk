import argparse
import json
import os
import re
import sys
from pathlib import Path

# Get project root (parent directory of mirrordash_core)
ROOT_DIR = Path(__file__).parent.parent.resolve()

def main():
    parser = argparse.ArgumentParser(description="MirrorDash developer CLI")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")
    
    # create-module sub-command
    create_parser = subparsers.add_parser("create-module", help="Bootstrap a new custom module")
    create_parser.add_argument("name", help="Name of the module (e.g., mirrordash-clock or mirrordash_weather)")
    create_parser.add_argument("--description", "-d", default="A custom module for MirrorDash", help="Module description")
    create_parser.add_argument("--author", "-a", default="MirrorDash Developer", help="Module author name")
    create_parser.add_argument("--dry-run", action="store_true", help="Preview generated files without creating them")
    
    # validate sub-command
    validate_parser = subparsers.add_parser("validate", help="Validate a module's structure and conformity")
    validate_parser.add_argument("path", nargs="?", default=".", help="Path to the module directory (default: current directory)")
    
    # register sub-command
    register_parser = subparsers.add_parser("register", help="Install module in editable mode and register in config.json")
    register_parser.add_argument("path", nargs="?", default=".", help="Path to the module directory (default: current directory)")
    
    args = parser.parse_args()
    
    if args.command == "create-module":
        create_module(args.name, args.description, args.author, args.dry_run)
    elif args.command == "validate":
        validate_module(args.path)
    elif args.command == "register":
        register_module(args.path)
    else:
        parser.print_help()

def create_module(name: str, description: str, author: str, dry_run: bool = False):
    # Normalize name:
    # Folder name: hyphens preferred for packaging, e.g., mirrordash-my-widget
    # Python package name: must use underscores, e.g., mirrordash_my_widget
    folder_name = name.lower().replace("_", "-")
    package_name = name.lower().replace("-", "_")
    
    # Generate dynamic class name (e.g. mirrordash_clock -> ClockModule)
    clean_name = package_name.replace("mirrordash_", "").replace("mymm_", "")
    class_name = "".join(word.capitalize() for word in clean_name.split("_")) + "Module"
    
    if not re.match(r"^[a-z0-9\-]+$", folder_name):
        print(f"Error: Invalid module name '{name}'. Only alphanumeric characters, hyphens, and underscores are allowed.", file=sys.stderr)
        sys.exit(1)
        
    if not folder_name.startswith("mirrordash-"):
        print(f"Warning: Module name '{name}' does not start with the 'mirrordash-' prefix. "
              f"It is recommended to use the 'mirrordash-' prefix (e.g. mirrordash-{clean_name}) "
              f"to prevent namespace pollution and comply with packaging standards.")
        
    cwd_modules_dir = Path.cwd() / "modules"
    modules_dir = ROOT_DIR / "modules"
    if cwd_modules_dir.exists() and cwd_modules_dir.is_dir():
        target_dir = cwd_modules_dir / folder_name
    elif modules_dir.exists() and modules_dir.is_dir():
        target_dir = modules_dir / folder_name
    else:
        target_dir = Path.cwd() / folder_name
        
    if not dry_run and target_dir.exists():
        print(f"Error: Directory '{target_dir}' already exists.", file=sys.stderr)
        sys.exit(1)
        
    prefix = "[DRY RUN] Would create" if dry_run else "Creating"
    print(f"{prefix} module '{folder_name}' in {target_dir}...")
    
    # Create directory structure
    package_dir = target_dir / package_name
    if not dry_run:
        package_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Write pyproject.toml
    pyproject_content = f"""[project]
name = "{folder_name}"
version = "0.1.0"
description = "{description}"
requires-python = ">=3.14"
authors = [
    {{ name = "{author}" }}
]
dependencies = [
    "jinja2"
]

[project.entry-points."mirrordash.modules"]
{package_name} = "{package_name}.plugin:{class_name}"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["{package_name}"]
"""
    if dry_run:
        print(f"\n[DRY RUN] Would write file: {target_dir / 'pyproject.toml'} with content:\n{pyproject_content.strip()}")
    else:
        with open(target_dir / "pyproject.toml", "w", encoding="utf-8") as f:
            f.write(pyproject_content)
        
    # 2. Write __init__.py
    init_content = "# Package initializer\n"
    if dry_run:
        print(f"\n[DRY RUN] Would write file: {package_dir / '__init__.py'} with content:\n{init_content.strip()}")
    else:
        with open(package_dir / "__init__.py", "w", encoding="utf-8") as f:
            f.write(init_content)
        
    # 3. Write config_schema.json
    title_val = folder_name.replace('mirrordash-', '').replace('mymm-', '').replace('_', ' ').replace('-', ' ').title()
    schema_content = f"""{{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "{title_val}",
  "type": "object",
  "properties": {{
    "enabled": {{
      "type": "boolean",
      "default": true,
      "title": "Enabled",
      "description": "Enable or disable this module."
    }},
    "position": {{
      "type": "string",
      "default": "middle_center",
      "enum": [
        "top_left",
        "top_center",
        "top_right",
        "middle_left",
        "middle_center",
        "middle_right",
        "bottom_left",
        "bottom_center",
        "bottom_right"
      ],
      "title": "Screen Position",
      "description": "Where to display this module on the mirror screen."
    }},
    "interval": {{
      "type": "integer",
      "default": 30,
      "title": "Update Interval (Seconds)",
      "description": "Time to wait between data refreshes."
    }},
    "show_header": {{
      "type": "boolean",
      "default": true,
      "title": "Show Header",
      "description": "Show or hide the module's header/title."
    }}
  }},
  "required": ["enabled", "position", "interval", "show_header"]
}}
"""
    if dry_run:
        print(f"\n[DRY RUN] Would write file: {package_dir / 'config_schema.json'} with content:\n{schema_content.strip()}")
    else:
        with open(package_dir / "config_schema.json", "w", encoding="utf-8") as f:
            f.write(schema_content)

    # 4. Write plugin.py
    plugin_content = f"""import asyncio
import logging
import os
from datetime import datetime

logger = logging.getLogger("mirrordash.modules.{package_name}")

class {class_name}:
    # Prevent pytest from trying to collect this class as a test case/suite
    __test__ = False

    def __init__(self, config):
        self.config = config
        self.name = "{package_name}"
        self.interval = config.get("interval", 30)
        
        # Writable data directory (persistent, backed up) and cache directory (transient, excluded from backups)
        self.data_dir = config.get("data_dir")
        self.cache_dir = config.get("cache_dir")
        
        # Translation dictionary containing strings merged from translations/*.json files
        self.translations = config.get("translations", {{}})
        
        # Event Bus for inter-module communication (pub/sub)
        self.event_bus = config.get("event_bus")
        
        logger.info(f"Initializing {{self.name}} module")

    async def run_loop(self, broadcast_func):
        \"\"\"
        The main lifecycle loop. Fetch data, format HTML, and broadcast.
        If you want to use a synchronous blocking loop instead, simply remove 'async'
        from the signature (def run_loop) and call broadcast_func synchronously.
        \"\"\"
        logger.info(f"Starting {{self.name}} run loop")
        while True:
            try:
                # 1. Fetch or compute your module's data here (e.g. caches, REST APIs)
                current_time = datetime.now().strftime("%H:%M:%S")
                
                # 2. Render dynamic HTML using Jinja2 template
                # (self.render_template is automatically injected by the core module loader
                # if your module package contains a 'templates' directory)
                html = self.render_template(
                    "widget.html",
                    current_time=current_time
                )
                
                # 3. Broadcast HTML update to the UI (no per-tick log to prevent spam)
                await broadcast_func(self.name, html)
                
            except asyncio.CancelledError:
                logger.info(f"{{self.name}} module stopped.")
                raise
            except Exception as e:
                logger.error(f"Error in module {{self.name}} run_loop: {{e}}")
                
            await asyncio.sleep(self.interval)
"""
    if dry_run:
        print(f"\n[DRY RUN] Would write file: {package_dir / 'plugin.py'} with content:\n{plugin_content.strip()}")
    else:
        with open(package_dir / "plugin.py", "w", encoding="utf-8") as f:
            f.write(plugin_content)

    # 4.5. Write translation JSON files
    translations_dir = package_dir / "translations"
    title_val = folder_name.replace('mirrordash-', '').replace('mymm-', '').replace('_', ' ').replace('-', ' ').title()
    en_trans = f"""{{
  "title": "{title_val}",
  "last_checked": "Last checked"
}}
"""
    sv_trans = f"""{{
  "title": "{title_val}",
  "last_checked": "Senast kontrollerad"
}}
"""
    if dry_run:
        print(f"\n[DRY RUN] Would create translations directory: {translations_dir}")
        print(f"[DRY RUN] Would write translations file: {translations_dir / 'en.json'} with content:\n{en_trans.strip()}")
        print(f"[DRY RUN] Would write translations file: {translations_dir / 'sv.json'} with content:\n{sv_trans.strip()}")
    else:
        translations_dir.mkdir(parents=True, exist_ok=True)
        with open(translations_dir / "en.json", "w", encoding="utf-8") as f:
            f.write(en_trans)
        with open(translations_dir / "sv.json", "w", encoding="utf-8") as f:
            f.write(sv_trans)

    # 5. Write templates/widget.html (Ethereal Design Compliant)
    templates_dir = package_dir / "templates"
    widget_content = f"""<div class="{folder_name}-container">
    {{% if show_header %}}
    <h2 class="module-header label-caps">{{{{ translations.get("title", "{title_val}") }}}}</h2>
    {{% endif %}}
    <div class="widget-content">
        <p class="last-checked">
            {{{{ translations.get("last_checked", "Last checked") }}}}: 
            <span class="time-value">{{{{ current_time }}}}</span>
        </p>
    </div>
</div>

<style>
.{folder_name}-container {{
    display: flex;
    flex-direction: column;
    width: 100%;
}}

.{folder_name}-container .widget-content {{
    margin-top: var(--label-gap, 8px);
}}

.{folder_name}-container .last-checked {{
    font-size: 14px;
    color: var(--color-standard-gray, #999999);
}}

.{folder_name}-container .time-value {{
    color: var(--color-high-contrast, #ffffff);
    font-weight: 500;
}}
</style>
"""
    if dry_run:
        print(f"\n[DRY RUN] Would create templates directory: {templates_dir}")
        print(f"[DRY RUN] Would write template: {templates_dir / 'widget.html'} with content:\n{widget_content.strip()}")
    else:
        templates_dir.mkdir(parents=True, exist_ok=True)
        with open(templates_dir / "widget.html", "w", encoding="utf-8") as f:
            f.write(widget_content)

    # 5.5. Write tests/test_plugin.py (Starter Tests)
    tests_dir = target_dir / "tests"
    test_content = f"""import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from {package_name}.plugin import {class_name}

def test_module_initialization():
    config = {{
        "interval": 15,
        "globals": {{
            "language": "en",
            "timezone": "Europe/Stockholm"
        }}
    }}
    module = {class_name}(config)
    assert module.name == "{package_name}"
    assert module.interval == 15

@pytest.mark.asyncio
async def test_module_run_loop():
    config = {{
        "interval": 30,
        "globals": {{
            "language": "en"
        }}
    }}
    module = {class_name}(config)
    
    # Mock render_template
    module.render_template = MagicMock(return_value="<div>Mock Render</div>")
    
    # Mock broadcast_func and patch asyncio.sleep to break the loop
    broadcast_mock = AsyncMock()
    with patch("asyncio.sleep", side_effect=asyncio.CancelledError):
        with pytest.raises(asyncio.CancelledError):
            await module.run_loop(broadcast_mock)
            
    # Verify the mock broadcast was called
    broadcast_mock.assert_called_once_with("{package_name}", "<div>Mock Render</div>")
"""
    if dry_run:
        print(f"\n[DRY RUN] Would create tests directory: {tests_dir}")
        print(f"[DRY RUN] Would write test file: {tests_dir / 'test_plugin.py'} with content:\n{test_content.strip()}")
    else:
        tests_dir.mkdir(parents=True, exist_ok=True)
        with open(tests_dir / "test_plugin.py", "w", encoding="utf-8") as f:
            f.write(test_content)
        
    # 6. Write README.md
    readme_content = f"""# {folder_name}
 
{description}
 
## Installation
 
Install in editable mode for local development:
```bash
uv pip install -e .
```

## Running Tests

Run the starter tests using pytest:
```bash
pytest
```

## Configuration & API Keys

Provide instructions here on how to retrieve necessary API keys or other credentials.
* **API Key Retrieval**: (e.g., "Sign up at [Provider Portal](https://example.com) to get your API key.")
* **Setup**: Enter the credentials in the visual configuration editor in the Admin Dashboard.

## Screenshot

Place a preview screenshot of your widget named `screenshot.png` in the root of this module directory. This image will be displayed inside the MirrorDash module store.

![Screenshot](screenshot.png)
"""
    if dry_run:
        print(f"\n[DRY RUN] Would write file: {target_dir / 'README.md'} with content:\n{readme_content.strip()}")
    else:
        with open(target_dir / "README.md", "w", encoding="utf-8") as f:
            f.write(readme_content)

    if not dry_run:
        print("\nSuccess! Module bootstrapped successfully.")
        print("Next steps:")
        # Calculate relative path from cwd
        try:
            rel_path = os.path.relpath(target_dir, start=os.getcwd())
        except Exception:
            rel_path = str(target_dir)
        print(f"  1. Navigate to: cd {rel_path}")
        print("  2. Install in editable mode: uv pip install -e .")
        print("  3. Register your module in the central config.json under modules.")
        print("  4. Restart MirrorDash to load the new module.")
    else:
        print("\nDry run completed. No files were written.")

def validate_module(path_str: str, exit_on_fail: bool = True) -> bool:
    try:
        import tomllib
    except ImportError:
        print("Error: tomllib is required (Python 3.11+). Please run with Python 3.11 or newer.", file=sys.stderr)
        if exit_on_fail:
            sys.exit(1)
        return False

    path = Path(path_str).resolve()
    print(f"Validating module at: {path}\n")

    pyproject_path = path / "pyproject.toml"
    if not pyproject_path.exists():
        print(f"  [✗] pyproject.toml not found. Is this a Python project directory?", file=sys.stderr)
        if exit_on_fail:
            sys.exit(1)
        return False

    has_errors = False
    has_warnings = False

    # 1. Parse pyproject.toml
    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)
        print("  [✓] pyproject.toml is valid TOML")
    except Exception as e:
        print(f"  [✗] Failed to parse pyproject.toml: {e}", file=sys.stderr)
        if exit_on_fail:
            sys.exit(1)
        return False

    # Check project name
    proj_name = pyproject_data.get("project", {}).get("name", "")
    if not proj_name:
        print("  [✗] Project name not defined in pyproject.toml")
        has_errors = True
    else:
        if not proj_name.startswith("mirrordash-"):
            print(f"  [!] Warning: Project name '{proj_name}' does not start with 'mirrordash-' prefix.")
            has_warnings = True
        else:
            print(f"  [✓] Project name '{proj_name}' is valid")

    # Check requires-python
    requires_python = pyproject_data.get("project", {}).get("requires-python", "")
    if not requires_python:
        print("  [!] Warning: 'requires-python' is not specified in pyproject.toml.")
        has_warnings = True
    else:
        print(f"  [✓] requires-python is specified: '{requires_python}'")

    # Check entry point
    entry_points = pyproject_data.get("project", {}).get("entry-points", {}).get("mirrordash.modules", {})
    if not entry_points:
        print("  [✗] No entry point registered under [project.entry-points.\"mirrordash.modules\"]")
        has_errors = True
        package_python_name = None
        class_name = None
    else:
        entry_name, entry_val = list(entry_points.items())[0]
        print(f"  [✓] Found entry point: {entry_name} = {entry_val}")
        if ":" not in entry_val:
            print("  [✗] Entry point target must be in format 'package.module:Class'")
            has_errors = True
            package_python_name = None
            class_name = None
        else:
            module_path, class_name = entry_val.split(":", 1)
            package_python_name = module_path.split(".", 1)[0]

    # 2. Check Package Directory
    package_dir = None
    if package_python_name:
        package_dir = path / package_python_name
        if not package_dir.exists() or not package_dir.is_dir():
            print(f"  [✗] Package directory '{package_python_name}' not found under project root.")
            has_errors = True
            package_dir = None
        else:
            print(f"  [✓] Package directory '{package_python_name}' exists")

    if package_dir:
        # Check __init__.py
        init_file = package_dir / "__init__.py"
        if not init_file.exists():
            print("  [✗] __init__.py not found in package directory.")
            has_errors = True
        else:
            print("  [✓] __init__.py exists")

        # Check plugin.py
        plugin_file = package_dir / "plugin.py"
        if not plugin_file.exists():
            print("  [✗] plugin.py not found in package directory.")
            has_errors = True
        else:
            print("  [✓] plugin.py exists")
            # Read and inspect plugin.py
            with open(plugin_file, "r", encoding="utf-8") as f:
                plugin_content = f.read()

            if class_name and f"class {class_name}" not in plugin_content:
                print(f"  [✗] Entrypoint class '{class_name}' is not defined in plugin.py.")
                has_errors = True
            elif class_name:
                print(f"  [✓] Entrypoint class '{class_name}' exists in plugin.py")

            # Check CancelledError
            if "CancelledError" not in plugin_content:
                print("  [✗] plugin.py does not appear to catch and re-raise asyncio.CancelledError.")
                print("      Every MirrorDash module run_loop must handle CancelledError cleanly (Rule #5).")
                has_errors = True
            else:
                print("  [✓] plugin.py references CancelledError (clean shutdown support)")

        # Check config_schema.json or plugin.py config_schema attribute
        schema_file = package_dir / "config_schema.json"
        has_schema = False
        schema_data = None
        if schema_file.exists():
            try:
                with open(schema_file, "r", encoding="utf-8") as sf:
                    schema_data = json.load(sf)
                print("  [✓] config_schema.json exists and is valid JSON")
                has_schema = True
            except Exception as se:
                print(f"  [✗] config_schema.json exists but is invalid JSON: {se}")
                has_errors = True
        else:
            # Check plugin.py
            if (package_dir / "plugin.py").exists() and f"config_schema" in plugin_content:
                print("  [✓] Inline config_schema attribute detected in plugin.py")
                has_schema = True
            else:
                print("  [!] Warning: No config_schema.json or inline config_schema attribute found.")
                print("      The module will fallback to default position/interval settings.")
                has_warnings = True

        # Validate schema details if config_schema.json is present
        if schema_data:
            properties = schema_data.get("properties", {})
            required_props = ["enabled", "position", "interval", "show_header"]
            missing_props = [p for p in required_props if p not in properties]
            if missing_props:
                print(f"  [!] Warning: config_schema is missing standard properties: {missing_props}")
                has_warnings = True
            else:
                print("  [✓] config_schema contains standard properties (enabled, position, interval, show_header)")

            # Check positions enum
            pos_prop = properties.get("position", {})
            enum_vals = pos_prop.get("enum", [])
            expected_positions = ["top_left", "top_center", "top_right", "middle_left", "middle_center", "middle_right", "bottom_left", "bottom_center", "bottom_right"]
            missing_positions = [pos for pos in expected_positions if pos not in enum_vals]
            if missing_positions:
                print(f"  [!] Warning: config_schema position enum only contains {len(enum_vals)} positions.")
                print(f"      Missing: {missing_positions}")
                has_warnings = True
            else:
                print("  [✓] config_schema position enum supports all 9 MirrorDash positions")

        # Check templates/widget.html
        templates_dir = package_dir / "templates"
        if not templates_dir.exists() or not templates_dir.is_dir():
            print("  [!] Warning: 'templates' directory not found.")
            has_warnings = True
        else:
            html_files = list(templates_dir.glob("*.html"))
            if not html_files:
                print("  [✗] No HTML template files (*.html) found in templates directory.")
                has_errors = True
            else:
                print(f"  [✓] Templates folder contains {len(html_files)} template(s): {[f.name for f in html_files]}")
                # Check Ethereal design style in html files
                for html_file in html_files:
                    with open(html_file, "r", encoding="utf-8") as hf:
                        h_content = hf.read()
                    if "<style>" not in h_content:
                        print(f"  [!] Warning: Template {html_file.name} does not contain a <style> block for module CSS isolation.")
                        has_warnings = True
                    if "show_header" not in h_content:
                        print(f"  [!] Warning: Template {html_file.name} does not reference 'show_header' context variable.")
                        has_warnings = True

        # Check translations/en.json
        translations_dir = package_dir / "translations"
        if not translations_dir.exists() or not translations_dir.is_dir():
            print("  [!] Warning: 'translations' directory not found.")
            has_warnings = True
        else:
            en_json = translations_dir / "en.json"
            if not en_json.exists():
                print("  [✗] English fallback translation file (translations/en.json) not found.")
                has_errors = True
            else:
                try:
                    with open(en_json, "r", encoding="utf-8") as tf:
                        json.load(tf)
                    print("  [✓] Fallback translation file translations/en.json is valid JSON")
                except Exception as te:
                    print(f"  [✗] translations/en.json is invalid JSON: {te}")
                    has_errors = True

    # 3. Check README.md and screenshot.png
    readme_file = path / "README.md"
    if not readme_file.exists():
        print("  [✗] README.md not found in module directory.")
        has_errors = True
    else:
        print("  [✓] README.md exists")
        with open(readme_file, "r", encoding="utf-8") as rf:
            readme_content = rf.read()
        if "screenshot.png" not in readme_content:
            print("  [!] Warning: README.md does not reference 'screenshot.png'.")
            has_warnings = True
        else:
            print("  [✓] README.md references screenshot.png")

    screenshot_file = path / "screenshot.png"
    if not screenshot_file.exists():
        print("  [!] Warning: screenshot.png not found in module directory.")
        print("      Every MirrorDash module should have a screenshot.png preview at its root for the module store.")
        has_warnings = True
    else:
        print("  [✓] screenshot.png exists")

    # Conclusion
    print("\nValidation Complete:")
    if has_errors:
        print("  STATUS: FAIL (Fix errors before distributing / enabling)")
        if exit_on_fail:
            sys.exit(1)
        return False
    elif has_warnings:
        print("  STATUS: PASS WITH WARNINGS (Ready, but clean up warnings for best practice)")
    else:
        print("  STATUS: PASS (100% MirrorDash Compliant)")
    return True

def register_module(path_str: str):
    try:
        import tomllib
    except ImportError:
        print("Error: tomllib is required (Python 3.11+). Please run with Python 3.11 or newer.", file=sys.stderr)
        sys.exit(1)
        
    import subprocess
    
    path = Path(path_str).resolve()
    pyproject_path = path / "pyproject.toml"
    
    # 1. Validate module first (without exiting immediately inside validation)
    print(f"Validating module at '{path}' before registering...")
    if not validate_module(path_str, exit_on_fail=False):
        print("\nError: Module validation failed. Registration aborted.", file=sys.stderr)
        sys.exit(1)
        
    # 2. Parse pyproject.toml to find module entry name and class name
    try:
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomllib.load(f)
    except Exception as e:
        print(f"Error: Failed to parse pyproject.toml: {e}", file=sys.stderr)
        sys.exit(1)
        
    entry_points = pyproject_data.get("project", {}).get("entry-points", {}).get("mirrordash.modules", {})
    if not entry_points:
        print("Error: No entry point registered under [project.entry-points.\"mirrordash.modules\"]", file=sys.stderr)
        sys.exit(1)
        
    entry_name = list(entry_points.keys())[0]
    
    # 3. Read config_schema.json to extract default properties
    schema_path = path / entry_name / "config_schema.json"
    default_config = {
        "enabled": True,
        "position": "top_left",
        "interval": 30
    }
    if schema_path.exists():
        try:
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_data = json.load(f)
            properties = schema_data.get("properties", {})
            for key, val in properties.items():
                if isinstance(val, dict) and "default" in val:
                    default_config[key] = val["default"]
        except Exception as e:
            print(f"Warning: Failed to extract schema defaults: {e}. Using fallback defaults.")

    # 4. Install the module in editable mode
    print(f"\nInstalling module '{entry_name}' in editable mode...")
    
    # Attempt uv first, fall back to robust python pip execution
    try:
        subprocess.run(["uv", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        install_cmd = ["uv", "pip", "install", "-e", str(path)]
    except (subprocess.CalledProcessError, FileNotFoundError):
        install_cmd = [sys.executable, "-m", "pip", "install", "-e", str(path)]
        
    print(f"Running: {' '.join(install_cmd)}")
    res = subprocess.run(install_cmd)
    if res.returncode != 0:
        print(f"\nError: Installation failed with exit code {res.returncode}.", file=sys.stderr)
        sys.exit(1)
        
    # 5. Resolve config.json path
    env_path = os.environ.get("MIRRORDASH_CONFIG_PATH") or os.environ.get("MYMM_CONFIG_PATH")
    if env_path:
        config_path = Path(env_path).resolve()
    else:
        config_path = Path(os.path.expanduser("~")) / ".mirrordash" / "data" / "config.json"
        if not config_path.exists():
            alt_paths = [
                Path(os.path.expanduser("~")) / ".mirrordash" / "config.json",
                Path(os.path.expanduser("~")) / ".mymagicmirror" / "config.json"
            ]
            for p in alt_paths:
                if p.exists():
                    config_path = p
                    break
                    
    # 6. Load and update config.json
    config = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load existing config.json: {e}")
            
    if not isinstance(config, dict):
        config = {}
        
    if "modules" not in config:
        config["modules"] = {}
        
    # Insert or update entry
    config["modules"][entry_name] = default_config
    
    # Save back to config.json
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        print(f"\n[✓] Registered module in config: {config_path}")
        print(f"    Key: '{entry_name}'")
        print(f"    Value: {json.dumps(default_config)}")
    except Exception as e:
        print(f"Error: Failed to save updated config.json: {e}", file=sys.stderr)
        sys.exit(1)
        
    print("\nSuccess! Module registered and ready for development.")
    print("Run your MirrorDash server locally:")
    print("  python -m mirrordash_core.main")

if __name__ == "__main__":
    main()
