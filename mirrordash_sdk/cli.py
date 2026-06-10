import argparse
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
    
    args = parser.parse_args()
    
    if args.command == "create-module":
        create_module(args.name, args.description, args.author)
    else:
        parser.print_help()

def create_module(name: str, description: str, author: str):
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
        
    cwd_modules_dir = Path.cwd() / "modules"
    modules_dir = ROOT_DIR / "modules"
    if cwd_modules_dir.exists() and cwd_modules_dir.is_dir():
        target_dir = cwd_modules_dir / folder_name
    elif modules_dir.exists() and modules_dir.is_dir():
        target_dir = modules_dir / folder_name
    else:
        target_dir = Path.cwd() / folder_name
        
    if target_dir.exists():
        print(f"Error: Directory '{target_dir}' already exists.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Creating module '{folder_name}' in {target_dir}...")
    
    # Create directory structure
    package_dir = target_dir / package_name
    package_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Write pyproject.toml
    pyproject_content = f"""[project]
name = "{folder_name}"
version = "0.1.0"
description = "{description}"
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
    with open(target_dir / "pyproject.toml", "w", encoding="utf-8") as f:
        f.write(pyproject_content)
        
    # 2. Write __init__.py
    with open(package_dir / "__init__.py", "w", encoding="utf-8") as f:
        f.write("# Package initializer\n")
        
    # 3. Write config_schema.json
    schema_content = """{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Custom Module Settings",
  "type": "object",
  "properties": {
    "enabled": {
      "type": "boolean",
      "default": true,
      "title": "Enabled",
      "description": "Enable or disable this module."
    },
    "position": {
      "type": "string",
      "default": "middle_center",
      "enum": ["top_left", "top_right", "middle_center", "bottom_left", "bottom_right"],
      "title": "Screen Position",
      "description": "Where to display this module on the mirror screen."
    },
    "interval": {
      "type": "integer",
      "default": 30,
      "title": "Update Interval (Seconds)",
      "description": "Time to wait between data refreshes."
    }
  },
  "required": ["enabled", "position", "interval"]
}
"""
    with open(package_dir / "config_schema.json", "w", encoding="utf-8") as f:
        f.write(schema_content)

    # 4. Write plugin.py
    plugin_content = f"""import asyncio
import logging
import os
from datetime import datetime

logger = logging.getLogger("mirrordash.modules.{package_name}")

class {class_name}:
    def __init__(self, config):
        self.config = config
        self.name = "{package_name}"
        self.interval = config.get("interval", 30)
        
        # Writable data directory (persistent, backed up) and cache directory (transient, excluded from backups)
        self.data_dir = config.get("data_dir")
        self.cache_dir = config.get("cache_dir")
        
        # Translation dictionary containing strings merged from translations/*.json files
        self.translations = config.get("translations", {{}})
        # To get a translated string in Python code (e.g. self.translate("my_key", "Default Value")):
        # title = self.translate("title", "Default Title")
        
        # Event Bus for inter-module communication (pub/sub)
        self.event_bus = config.get("event_bus")
        # To subscribe to events from other modules:
        # if self.event_bus:
        #     self.event_bus.subscribe("some_event", self.handle_some_event)
        
        logger.info(f"Initializing {{self.name}} module")

    # Example event handler callback:
    # def handle_some_event(self, data):
    #     logger.info(f"{{self.name}} received event data: {{data}}")

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
                
                # To publish an event to other modules:
                # if self.event_bus:
                #     self.event_bus.publish("{package_name}:tick", {{"time": current_time}})
                
                # 2. Render dynamic HTML using Jinja2 template
                # (self.render_template is automatically injected by the core module loader
                # if your module package contains a 'templates' directory)
                html = self.render_template(
                    "widget.html",
                    current_time=current_time
                )
                
                # 3. Broadcast HTML update to the UI
                logger.info(f"Broadcasting update for {{self.name}}")
                await broadcast_func(self.name, html)
                
            except Exception as e:
                logger.error(f"Error in module {{self.name}} run_loop: {{e}}")
                
            await asyncio.sleep(self.interval)
"""
    with open(package_dir / "plugin.py", "w", encoding="utf-8") as f:
        f.write(plugin_content)

    # 4.5. Write translation JSON files
    translations_dir = package_dir / "translations"
    translations_dir.mkdir(parents=True, exist_ok=True)
    
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
    with open(translations_dir / "en.json", "w", encoding="utf-8") as f:
        f.write(en_trans)
    with open(translations_dir / "sv.json", "w", encoding="utf-8") as f:
        f.write(sv_trans)

    # 5. Write templates/widget.html
    templates_dir = package_dir / "templates"
    templates_dir.mkdir(parents=True, exist_ok=True)
    widget_content = """<div class="custom-widget-container">
    <h3>{{ translations.get("title", "Custom Widget") }}</h3>
    <p>{{ translations.get("last_checked", "Last checked") }}: {{ current_time }}</p>
</div>
"""
    with open(templates_dir / "widget.html", "w", encoding="utf-8") as f:
        f.write(widget_content)
        
    # 6. Write README.md
    readme_content = f"""# {folder_name}
 
{description}
 
## Installation
 
Install in editable mode for local development:
```bash
uv pip install -e .
```

## Configuration & API Keys

Provide instructions here on how to retrieve necessary API keys or other credentials.
* **API Key Retrieval**: (e.g., "Sign up at [Provider Portal](https://example.com) to get your API key.")
* **Setup**: Enter the credentials in the visual configuration editor in the Admin Dashboard.

## Screenshot

Place a preview screenshot of your widget named `screenshot.png` in the root of this module directory. This image will be displayed inside the MirrorDash module store.

![Screenshot](screenshot.png)
"""
    with open(target_dir / "README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)

    print("Success! Module bootstrapped successfully.")
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

if __name__ == "__main__":
    main()
