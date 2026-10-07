import os
import re
import sys
from pathlib import Path

# Get project root (parent directory of mirrordash_core)
ROOT_DIR = Path(__file__).parent.parent.resolve()

def create_module(name: str, description: str, author: str, icon: str = None, dry_run: bool = False):
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
        
    # Resolve icon:
    icon_svg_content = None
    icon_fa_class = None

    if icon:
        if icon.lower().endswith(".svg"):
            icon_path = Path(icon)
            if icon_path.exists() and icon_path.is_file():
                try:
                    icon_svg_content = icon_path.read_text(encoding="utf-8").strip()
                except Exception as e:
                    print(f"Error reading custom SVG icon file '{icon}': {e}", file=sys.stderr)
                    sys.exit(1)
            else:
                print(f"Error: Custom SVG icon file '{icon}' not found.", file=sys.stderr)
                sys.exit(1)
        else:
            icon_fa_class = icon
    else:
        # Default SVG icon (3D Cube)
        icon_svg_content = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
  <polyline points="3.27 6.96 12 12.01 20.73 6.96"/>
  <line x1="12" y1="22.08" x2="12" y2="12"/>
</svg>"""

    # 3. Write config_schema.json
    title_val = folder_name.replace('mirrordash-', '').replace('mymm-', '').replace('_', ' ').replace('-', ' ').title()
    
    schema_root_fields = []
    schema_root_fields.append(f'"$schema": "http://json-schema.org/draft-07/schema#"')
    schema_root_fields.append(f'"title": "{title_val}"')
    if icon_fa_class:
        schema_root_fields.append(f'"icon": "{icon_fa_class}"')
    schema_root_fields.append('"type": "object"')

    properties_block = """  "properties": {
    "interval": {
      "type": "integer",
      "default": 30,
      "title": "Update Interval (Seconds)",
      "description": "Time to wait between data refreshes."
    },
    "show_header": {
      "type": "boolean",
      "default": true,
      "title": "Show Header",
      "description": "Show or hide the module's header/title."
    }
  },
  "required": ["interval", "show_header"]"""

    schema_content = "{\n  " + ",\n  ".join(schema_root_fields) + ",\n" + properties_block + "\n}\n"

    if dry_run:
        print(f"\n[DRY RUN] Would write file: {package_dir / 'config_schema.json'} with content:\n{schema_content.strip()}")
    else:
        with open(package_dir / "config_schema.json", "w", encoding="utf-8") as f:
            f.write(schema_content)

    # 3.b Write icon.svg if resolved
    if icon_svg_content:
        if dry_run:
            print(f"\n[DRY RUN] Would write file: {package_dir / 'icon.svg'} with content:\n{icon_svg_content.strip()}")
        else:
            with open(package_dir / "icon.svg", "w", encoding="utf-8") as f:
                f.write(icon_svg_content)

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

    # 7. Write .gitignore
    gitignore_content = """# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.venv/
venv/
build/
dist/
*.egg-info/

# IDE / Editors
.idea/
.vscode/
*.swp
*.swo

# System / OS
.DS_Store
Thumbs.db

# App local logs or cli tools cache
.antigravitycli/
.kilo/
"""
    if dry_run:
        print(f"\n[DRY RUN] Would write file: {target_dir / '.gitignore'} with content:\n{gitignore_content.strip()}")
        print("[DRY RUN] Would run: git init")
        print("[DRY RUN] Would run: git add .")
        print("[DRY RUN] Would run: git commit --no-gpg-sign -m \"feat: initial commit\"")
    else:
        with open(target_dir / ".gitignore", "w", encoding="utf-8") as f:
            f.write(gitignore_content)

    if not dry_run:
        # Initialize Git repository
        try:
            import subprocess
            import shutil
            if shutil.which("git"):
                print("Initializing Git repository...")
                subprocess.run(["git", "init"], cwd=target_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["git", "add", "."], cwd=target_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.run(["git", "commit", "--no-gpg-sign", "-m", "feat: initial commit"], cwd=target_dir, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print("Git repository initialized with initial commit.")
            else:
                print("Warning: 'git' command not found. Skipping Git repository initialization.")
        except Exception as e:
            print(f"Warning: Failed to initialize Git repository: {e}")

        print("\nSuccess! Module bootstrapped successfully.")
        print("Next steps:")
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
