# MirrorDash Developer CLI & Tools

This repository contains the developer command-line interface (`mirrordash-cli`) and documentation for bootstrapping and developing custom modules for the MirrorDash ambient display platform.

## Contents

- **`MODULE_GUIDE.md`**: Detailed API guide, translations, templates, and storage conventions for module development.
- **`MODULE_AGENTS.md`**: Guide and constraints for AI coding agents developing MirrorDash modules.
- **`mirrordash_cli/`**: Python source code for the bootstrapping utility.

## Installation

Install in editable mode in your development environment:

```bash
uv pip install -e .
```

Or install it globally:

```bash
uv pip install /path/to/mirrordash-cli
```

## Usage

Bootstrap a new custom module:

```bash
mirrordash-cli create-module mirrordash-my-widget --description "A custom widget"
```

This will automatically create a fully configured module skeleton inside your current workspace.
