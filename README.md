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
