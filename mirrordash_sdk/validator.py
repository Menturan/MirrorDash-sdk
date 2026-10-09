import ast
import json
import sys
from pathlib import Path

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
            plugin_content = ""
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
                print("      The module will only get the standard settings (enabled, position, …).")
                has_warnings = True

        # Validate schema details if config_schema.json is present
        if schema_data:
            properties = schema_data.get("properties", {})
            # The core adds these to every module's settings form; a module redeclaring them is ignored
            core_fields = ["enabled", "position", "carousel_group", "carousel_interval", "max_width", "max_height", "z_index", "opacity"]
            redeclared = [p for p in core_fields if p in properties]
            if redeclared:
                print(f"  [!] Warning: config_schema declares settings the core already provides: {redeclared}")
                print("      Remove them; the admin form ignores them and uses the core's own fields.")
                has_warnings = True
            else:
                print("  [✓] config_schema leaves the standard settings (enabled, position, …) to the core")
            # A key typed into the admin page shows in plain text unless the field says it's a password
            secret_words = ("key", "token", "secret", "password")
            unmasked = [name for name, prop in properties.items()
                        if any(word in name.lower() for word in secret_words)
                        and isinstance(prop, dict) and prop.get("format") != "password"]
            if unmasked:
                print(f"  [!] Warning: these settings look secret but show in plain text: {unmasked}")
                print('      Add "format": "password" to each so the admin page hides what is typed.')
                has_warnings = True

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
                for html_file in html_files:
                    with open(html_file, "r", encoding="utf-8") as hf:
                        h_content = hf.read()
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

        # An own HTTP client misses what self.fetch gives: sleeping while the screen is off, the last answer offline
        # ponytail: a plain import list; an import through a helper package or importlib slips past
        http_clients = ("requests", "httpx", "aiohttp", "urllib.request", "urllib3", "http.client", "pycurl", "websockets")
        own_fetching = []
        for py_file in sorted(package_dir.rglob("*.py")):
            if "tests" in py_file.relative_to(package_dir).parts:
                continue
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module] + [f"{node.module}.{a.name}" for a in node.names]
                else:
                    continue
                hit = next((n for n in names if any(n == c or n.startswith(c + ".") for c in http_clients)), None)
                if hit:
                    own_fetching.append(f"{py_file.relative_to(path)}:{node.lineno} ({hit})")
        if own_fetching:
            print(f"  [!] Warning: the module fetches data with its own HTTP client: {', '.join(own_fetching)}")
            print("      Use self.fetch_json / self.fetch instead. Your own client doesn't pause while the screen is off")
            print("      (it keeps calling the API at night) and has no offline fallback.")
            has_warnings = True
        else:
            print("  [✓] Fetches data through self.fetch / self.fetch_json")

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
        print("      Add a picture of the module named screenshot.png; your README shows it on GitHub.")
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
