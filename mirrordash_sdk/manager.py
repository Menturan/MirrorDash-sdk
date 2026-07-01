import json
import os
import sys
import subprocess
from pathlib import Path
import click

from .validator import validate_module

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
    print("  python -m mirrordash_core.main")

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
            subprocess.run(["uv", "venv", str(venv_path)], check=True)
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
    install_target = core_git if core_git else "mirrordash"
    print(f"Installing MirrorDash core ({install_target}) into venv...")
    
    use_uv = False
    try:
        res = subprocess.run(["uv", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0:
            use_uv = True
    except Exception:
        pass

    if use_uv:
        cmd = ["uv", "pip", "install", "--python", str(venv_python), install_target]
    else:
        cmd = [str(venv_python), "-m", "pip", "install", install_target]
        
    print(f"Running: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    
    # 4. Install and register module if editable is true
    if editable:
        pyproject_path = path / "pyproject.toml"
        if pyproject_path.exists():
            print("\nFound pyproject.toml in target path. Registering module...")
            register_module(str(path), python_exe=venv_python)
        else:
            print(f"\nWarning: --editable was set, but no pyproject.toml was found at {path}.", file=sys.stderr)
            
    print("\nSuccess! Development environment is set up.")
    print("To activate the virtual environment:")
    if os.name == "nt":
        print(f"  {venv_path}\\Scripts\\activate")
    else:
        print(f"  source {venv_path}/bin/activate")
    print("To start the MirrorDash server:")
    print("  mirrordash-cli start")

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
        
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\nMirrorDash server stopped.")

def build_module_logic(path_str: str):
    path = Path(path_str).resolve()
    
    pyproject_path = path / "pyproject.toml"
    if not pyproject_path.exists():
        print(f"Error: No pyproject.toml found at {path}. Can only build inside a python package directory.", file=sys.stderr)
        sys.exit(1)
        
    print(f"Building package at: {path}...")
    
    use_uv = False
    try:
        res = subprocess.run(["uv", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0:
            use_uv = True
    except Exception:
        pass
        
    if use_uv:
        cmd = ["uv", "build"]
    else:
        # Check if venv python has build, or use current interpreter
        venv_path = Path.cwd() / ".venv"
        if venv_path.exists():
            if os.name == "nt":
                venv_python = venv_path / "Scripts" / "python.exe"
            else:
                venv_python = venv_path / "bin" / "python"
            if venv_python.exists():
                cmd = [str(venv_python), "-m", "build"]
            else:
                cmd = [sys.executable, "-m", "build"]
        else:
            cmd = [sys.executable, "-m", "build"]
        print(f"Running build with command: {' '.join(cmd)}")
        print("Note: If this fails, ensure the 'build' package is installed ('pip install build').")
        
    res = subprocess.run(cmd, cwd=path)
    if res.returncode == 0:
        print(f"\n[✓] Successfully built module. Distribution files in: {path / 'dist'}")
    else:
        print(f"\nError: Build failed with exit code {res.returncode}", file=sys.stderr)
        sys.exit(res.returncode)

def publish_module_logic(path_str: str, force: bool = False):
    path = Path(path_str).resolve()
    
    # 1. Run validation
    print("Running module validation before publishing...")
    valid = validate_module(path_str, exit_on_fail=False)
    if not valid:
        if not force:
            if not click.confirm("Validation warnings or errors found. Do you want to publish anyway?"):
                print("Publishing aborted.")
                sys.exit(1)
        else:
            print("Validation failed, but --force is active. Proceeding to publish...")
            
    # 2. Check for build artifacts
    dist_dir = path / "dist"
    if not dist_dir.exists() or not list(dist_dir.glob("*")):
        print(f"Warning: No build distribution artifacts found in {dist_dir}.", file=sys.stderr)
        if click.confirm("Do you want to build the package first?"):
            build_module_logic(path_str)
        else:
            print("Publishing aborted. Build files are required.")
            sys.exit(1)
            
    # 3. Publish
    print(f"Publishing package at {path} to PyPI...")
    
    use_uv = False
    try:
        res = subprocess.run(["uv", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0:
            use_uv = True
    except Exception:
        pass
        
    if use_uv:
        cmd = ["uv", "publish"]
    else:
        # Check if venv python has twine, or use system/current interpreter
        venv_path = Path.cwd() / ".venv"
        if venv_path.exists():
            if os.name == "nt":
                venv_python = venv_path / "Scripts" / "python.exe"
            else:
                venv_python = venv_path / "bin" / "python"
            if venv_python.exists():
                cmd = [str(venv_python), "-m", "twine", "upload", "dist/*"]
            else:
                cmd = ["twine", "upload", "dist/*"]
        else:
            cmd = ["twine", "upload", "dist/*"]
        print(f"Running publish with command: {' '.join(cmd)}")
        print("Note: If this fails, ensure 'twine' is installed ('pip install twine') and PyPI credentials are set up.")
        
    res = subprocess.run(cmd, cwd=path)
    if res.returncode == 0:
        print("\n[✓] Successfully published module to PyPI!")
    else:
        print(f"\nError: Publish failed with exit code {res.returncode}", file=sys.stderr)
        sys.exit(res.returncode)
