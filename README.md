# MirrorDash Developer SDK & Tools

This repository contains the developer command-line interface (`mirrordash-cli`) and documentation for bootstrapping and developing custom modules for the MirrorDash ambient display platform.

## Contents

- **`MODULE_GUIDE.md`**: Detailed API guide, translations, templates, and storage conventions for module development.
- **`MODULE_AGENTS.md`**: Guide and constraints for AI coding agents developing MirrorDash modules.
- **`mirrordash_sdk/`**: Python source code for the bootstrapping utility.
- **Design System Explorer**: Served at `http://localhost:8000/design` when the server is running locally. It provides a live components catalog with copyable styling blocks and templates matching the Ethereal Design System.

## Installation & Running

You can run the CLI tool without cloning the repository using `uvx` (part of the `uv` toolchain):

```bash
# Run directly from PyPI
uvx mirrordash-cli create-module mirrordash-my-widget --description "A custom widget"

# Or run directly from Git
uvx --from git+https://github.com/menturan/mirrordash-sdk.git mirrordash-cli create-module mirrordash-my-widget --description "A custom widget"
```

### Local Development Installation

If you are developing the SDK itself or prefer a local installation:

```bash
# Install in editable mode
uv pip install -e .

# Or install from local path
uv pip install /path/to/mirrordash-sdk
```

After local installation, run it directly:

```bash
mirrordash-cli create-module mirrordash-my-widget --description "A custom widget"
```

This will automatically create a fully configured module skeleton inside your current workspace.
