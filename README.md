# 🛠️ MirrorDash Developer SDK & Tools

[![Python Version](https://img.shields.io/badge/python-3.14%2B-blue.svg)](#)
[![License: PolyForm_NC_1.0.0](https://img.shields.io/badge/license-PolyForm_NC_1.0.0-525252)](LICENSE.md)
[![Toolchain: uv](https://img.shields.io/badge/toolchain-uv-de5c84.svg)](#)

Welcome to the **MirrorDash Software Development Kit (SDK)**! This repository contains the developer command-line interface (`mirrordash-cli`) and documentation for bootstrapping and building beautiful custom modules for the MirrorDash ambient display platform.

Imagine taking calendar events, transit schedules, smart home sensors, or custom widgets and making them float elegantly on a heads-up display. That is what this SDK allows you to build.

---

## ⚡ Quick Start: Scaffold a Module in 3 Seconds!

You don't even need to clone this repository manually to start building! If you have the `uv` toolchain installed, run the scaffolder directly:

```bash
# Run directly from PyPI
uvx mirrordash-cli create-module mirrordash-my-widget --description "A custom display widget"
```

This creates a fully configured module skeleton containing:
* 📦 A pre-configured `pyproject.toml` (Hatchling build backend, correct entry point bindings).
* ⚙️ A visual dashboard configuration schema (`config_schema.json`).
* 🔌 A starter plugin module class (`plugin.py`) featuring async lifecycle loops.
* 🌐 Built-in localization support (`translations/en.json` & `translations/sv.json`).
* 🎨 An Ethereal-compliant responsive HTML template (`templates/widget.html`) with isolated CSS.
* 🧪 Starter unit tests (`tests/test_plugin.py`).

---

## 🛠️ How to Set Up & Develop Locally

To develop modules and test them in real-time, you can set up a local development virtual environment and run the MirrorDash server easily with the CLI.

### Step 1: Set Up a Virtual Environment & Core App
Run the developer setup tool in your development workspace directory:
```bash
# Auto-creates .venv and installs MirrorDash core inside it
uvx mirrordash-cli dev-setup
```

### Step 2: Scaffold Your Module
Use the SDK command-line tool to bootstrap a new custom module directory:
```bash
# Scaffold the module
uvx mirrordash-cli create-module mirrordash-my-widget --description "A custom widget"
```

### Step 3: Register and Enable Your Module
Validate your module, install it in editable mode inside your virtual environment, and register its default configuration settings in your local `config.json` automatically:
```bash
# Validate, install, and enable in config.json
uvx mirrordash-cli register ./mirrordash-my-widget
```

### Step 4: Start the MirrorDash Server
Run the core MirrorDash server automatically from your active virtual environment:
```bash
uvx mirrordash-cli start
```
*(Or simply run `mirrordash-cli start` if you have activated the virtual environment).*

Open `http://localhost:8000/` in your browser to view the live mirror HUD. Open `http://localhost:8000/design` to view the Design System Explorer. When you edit your module's Python or template files, changes will reload hot!

---

## ✨ Features & Bells

* **🚀 Hot-Reload Dev Setup**: Develop widgets locally in editable mode—changes reload instantly on server restart.
* **🎨 Design System Explorer**: Access `http://localhost:8000/design` during local development to browse a live interactive kitchen-sink showing typography scales, spacing tokens, and copy-pasteable component markup.
* **🔒 OverlayFS Compliant**: Out-of-the-box setup to write persistent files/databases to `self.data_dir` and temporary files to `self.cache_dir`, preserving SD card lifespans.
* **🌐 Automated Localization**: Dynamic dictionary merging that guarantees translation keys fall back cleanly to English if localized translations are missing.

---

## 📂 Repository Contents

* **[MODULE_GUIDE.md](file:///home/menturan/repos/mirrordash-sdk/MODULE_GUIDE.md)**: The developer's bible. Contains the API specification, translation rules, event bus usage, and styling guidelines.
* **[MODULE_AGENTS.md](file:///home/menturan/repos/mirrordash-sdk/MODULE_AGENTS.md)**: Rules and constraints designed specifically for AI coding agents developing MirrorDash modules.
* **`mirrordash_sdk/`**: Python CLI utility codebase driving the `mirrordash-cli` generator and validator.

---

## 🔧 Local Development & Command Reference

If you are developing the SDK tool itself or want to install it from source:

```bash
# Clone the repository and install in editable mode
uv pip install -e .
```

Once installed, use the full CLI commands reference:

```bash
# 1. Dev Environment & Server Management
mirrordash-cli dev-setup [options]   # Create .venv, install core, and optionally register module
                                    # Options: -p, --path; --core-git; -e, --editable
mirrordash-cli start [options]       # Start the MirrorDash local development server

# 2. Scaffolding & Registration
mirrordash-cli create-module <name>  # Scaffold a new widget directory structure
mirrordash-cli validate <path>       # Validate an existing widget structure and conformity
mirrordash-cli register <path>       # Validate, install in editable mode, and enable in config.json

# 3. Build & CI/CD Deployment
mirrordash-cli setup-github <path>   # Generate a GitHub Actions CI/CD workflow (publish.yml)
mirrordash-cli build <path>          # Build module wheels and source distribution package
mirrordash-cli publish <path>        # Run validation and upload package to PyPI
```

> [!IMPORTANT]
> **Check Out the Guide:** Before pushing your custom widget, check out [MODULE_GUIDE.md](file:///home/menturan/repos/mirrordash-sdk/MODULE_GUIDE.md) for full compliance instructions regarding vector icons (Lucide), responsive sizing, and OverlayFS directory conventions.
