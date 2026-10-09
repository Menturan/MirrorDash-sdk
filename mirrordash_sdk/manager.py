import json
import os
import sys
import subprocess
from pathlib import Path

from .validator import validate_module

# The oldest core that has what the module templates use (fetch_json, the layout classes)
CORE_REQUIREMENT = "mirrordash>=0.5"
CORE_GIT = "git+https://github.com/Menturan/MirrorDash.git"
DEV_URL = "http://localhost:8000/"
DEV_PASSWORD = "mirrordash"
# Runs in the dev venv: sets the admin password only if none is set, printing "set" when it did
SET_DEV_PASSWORD = """\
import secrets, sys
from mirrordash_core.config import load_config, save_config
try:
    from mirrordash_core.admin import hash_password
except ImportError:  # MirrorDash before the vertical slices (0.6.x)
    from mirrordash_core.api.admin_shared import hash_password
config = load_config()
if "admin_auth" not in config:
    salt = secrets.token_hex(16)
    config["admin_auth"] = {"hash": hash_password(sys.argv[1], salt), "salt": salt}
    save_config(config)
    print("set")
"""

def register_module(path_str: str, python_exe: Path = None):
    try:
        import tomllib
    except ImportError:
        print("Error: tomllib is required (Python 3.11+). Please run with Python 3.11 or newer.", file=sys.stderr)
        sys.exit(1)
        
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
        if python_exe:
            install_cmd = ["uv", "pip", "install", "--python", str(python_exe), "-e", str(path)]
        else:
            install_cmd = ["uv", "pip", "install", "-e", str(path)]
    except (subprocess.CalledProcessError, FileNotFoundError):
        pip_target = python_exe or sys.executable
        install_cmd = [str(pip_target), "-m", "pip", "install", "-e", str(path)]
        
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
    print("  mirrordash-sdk start")

def dev_setup_logic(path_str: str, core_git: str = None, editable: bool = False):
    path = Path(path_str).resolve()
    venv_path = path / ".venv"
    
    print(f"Setting up developer environment at: {path}")
    
    # 1. Create venv if not exists
    if not venv_path.exists():
        print(f"Creating virtual environment in {venv_path}...")
        # Check if uv is available
        use_uv = False
        try:
            res = subprocess.run(["uv", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0:
                use_uv = True
        except Exception:
            pass
            
        if use_uv:
            print("Using 'uv' to create virtual environment.")
            # The core needs Python 3.14; uv downloads it if this computer has an older one
            subprocess.run(["uv", "venv", "--python", "3.14", str(venv_path)], check=True)
        else:
            print("Using 'venv' module to create virtual environment.")
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)], check=True)
    else:
        print(f"Virtual environment already exists at {venv_path}")

    # 2. Get venv executables
    if os.name == "nt":
        venv_python = venv_path / "Scripts" / "python.exe"
    else:
        venv_python = venv_path / "bin" / "python"
        
    if not venv_python.exists():
        print(f"Error: Could not find Python interpreter in venv at {venv_python}", file=sys.stderr)
        sys.exit(1)

    # 3. Install MirrorDash core
    use_uv = False
    try:
        res = subprocess.run(["uv", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0:
            use_uv = True
    except Exception:
        pass

    def install(target, check):
        cmd = (["uv", "pip", "install", "--python", str(venv_python), target] if use_uv
               else [str(venv_python), "-m", "pip", "install", target])
        print(f"Installing MirrorDash core ({target}) into venv...\nRunning: {' '.join(cmd)}")
        return subprocess.run(cmd, check=check).returncode == 0

    # ponytail: until a core with everything the templates use is on PyPI, fall back to core's master.
    # Once it is released the first install succeeds and the fallback is never used.
    if core_git:
        install(core_git, check=True)
    elif not install(CORE_REQUIREMENT, check=False):
        print(f"\nCouldn't install {CORE_REQUIREMENT} from PyPI; installing the newest core from GitHub instead.")
        install(CORE_GIT, check=True)
    
    # 4. Install and register module if editable is true
    if editable:
        pyproject_path = path / "pyproject.toml"
        if pyproject_path.exists():
            print("\nFound pyproject.toml in target path. Registering module...")
            register_module(str(path), python_exe=venv_python)
        else:
            print(f"\nWarning: --editable was set, but no pyproject.toml was found at {path}.", file=sys.stderr)

    # 5. A fresh mirror shows only "set an admin password" until one is set, hiding the modules.
    # Set a known one for this dev mirror (if there's none yet), through the core's own code.
    res = subprocess.run([str(venv_python), "-c", SET_DEV_PASSWORD, DEV_PASSWORD], capture_output=True, text=True)
    if res.returncode == 0 and res.stdout.strip() == "set":
        print(f"\nAdmin page of this dev mirror: {DEV_URL}admin (password: {DEV_PASSWORD})")

    print("\nSuccess! Development environment is set up.")
    print("To activate the virtual environment:")
    if os.name == "nt":
        print(f"  {venv_path}\\Scripts\\activate")
    else:
        print(f"  source {venv_path}/bin/activate")
    print("To start the MirrorDash server:")
    print("  mirrordash-sdk start")

def open_when_ready(url: str = DEV_URL, wait: float = 60) -> None:
    """Open url in the browser as soon as the server answers (in the background, so the server can start)."""
    import threading
    import time
    import urllib.request
    import webbrowser

    def poll():
        deadline = time.monotonic() + wait
        while time.monotonic() < deadline:
            try:
                urllib.request.urlopen(url, timeout=2).close()
                webbrowser.open(url)
                return
            except OSError:
                time.sleep(1)
        print(f"The server didn't answer at {url} within {wait:.0f} seconds; open it yourself when it does.")

    threading.Thread(target=poll, daemon=True).start()

def start_server_logic(path_str: str):
    path = Path(path_str).resolve()
    
    # Try to find .venv
    venv_path = path / ".venv"
    if not venv_path.exists():
        # check parent directory
        venv_path = Path.cwd() / ".venv"
        
    if venv_path.exists():
        if os.name == "nt":
            venv_python = venv_path / "Scripts" / "python.exe"
        else:
            venv_python = venv_path / "bin" / "python"
        
        if venv_python.exists():
            cmd = [str(venv_python), "-m", "mirrordash_core.main"]
            print(f"Starting MirrorDash server using virtual environment python at {venv_python}...")
        else:
            cmd = ["python", "-m", "mirrordash_core.main"]
            print("Warning: .venv found but python executable missing. Starting MirrorDash server using system/global 'python'...")
    else:
        cmd = ["python", "-m", "mirrordash_core.main"]
        print("Warning: No local virtual environment (.venv) found. Starting MirrorDash server using system/global 'python'...")
        
    # Development mode: the mirror restarts by itself when a file in the module changes (.py, .html, .json, .css)
    print("Watching for changes: save a file and the mirror reloads it.")
    try:
        subprocess.run(cmd, cwd=path, env={**os.environ, "MIRRORDASH_DEV": "1"})
    except KeyboardInterrupt:
        print("\nMirrorDash server stopped.")
