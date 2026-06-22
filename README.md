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

To develop modules and test them in real-time, you can install the core MirrorDash application (`mirrordash`) directly into a local Python virtual environment. **You do not need to clone the core repository.**

### Step 1: Set Up a Virtual Environment
Create and activate a virtual environment in your development workspace:
```bash
# Create the virtual environment
uv venv

# Activate it
source .venv/bin/activate
```

### Step 2: Install the Core MirrorDash Application
Install the core application directly from PyPI (or from the official Git repository if you need the latest development builds):
```bash
# Install from PyPI
uv pip install mirrordash

# OR: Install from the official Git repository
uv pip install git+https://github.com/Menturan/MirrorDash.git
```

### Step 3: Scaffold Your Module
Use the SDK command-line tool to bootstrap a new custom module directory:
```bash
# Scaffold the module
uvx mirrordash-cli create-module mirrordash-my-widget --description "A custom widget"
```

### Step 4: Install Your Module in Editable Mode
Install your custom module into the active virtual environment in **editable mode** (`-e`). This tells Python to link directly to your source files, so any modifications to your templates or scripts take effect immediately:
```bash
# Install in editable mode
uv pip install -e ./mirrordash-my-widget
```

### Step 5: Enable Your Module in local Configuration
Your local MirrorDash settings are stored automatically at `~/.mirrordash/data/config.json`. Enable your widget and assign its screen position in the configuration:
```json
{
  "modules": {
    "mirrordash-my-widget": {
      "enabled": true,
      "position": "top_left",
      "interval": 60
    }
  }
}
```
*(Alternatively, configure it visually by opening the Admin Dashboard at `http://localhost:8000/admin` once the server starts).*

### Step 6: Start the MirrorDash Server
Run the core MirrorDash server from your active virtual environment:
```bash
python -m mirrordash_core.main
```
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

## 🔧 Local Development & Installation

If you are developing the SDK tool itself or want to install it from source:

```bash
# Clone the repository and install in editable mode
uv pip install -e .
```

Once installed, use the CLI directly:
```bash
# Bootstrap a widget
mirrordash-cli create-module mirrordash-my-widget

# Validate an existing widget directory structure
mirrordash-cli validate ./modules/mirrordash-my-widget
```

> [!IMPORTANT]
> **Check Out the Guide:** Before pushing your custom widget, check out [MODULE_GUIDE.md](file:///home/menturan/repos/mirrordash-sdk/MODULE_GUIDE.md) for full compliance instructions regarding vector icons (Lucide), responsive sizing, and OverlayFS directory conventions.
