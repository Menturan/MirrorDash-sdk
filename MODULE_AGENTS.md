# MODULE_AGENTS.md — MirrorDash Module AI Agent Guide

This file provides AI coding agents with instructions for creating, modifying, and testing custom modules for MirrorDash. Read this before developing any module.

---

## 1. Developer Environment & Scaffolding

### Setting Up the Environment
Always initialize the Python virtual environment and core packages using the CLI `dev-setup` command:
```bash
mirrordash-cli dev-setup
```

### Always Use the CLI Scaffolder
Never build module packages manually from scratch. Always scaffold a new module using the `create-module` command:
```bash
mirrordash-cli create-module mirrordash-<name> --description "<description>"
```
This ensures a fully compatible Hatchling project layout with the correct entry point registrations in `pyproject.toml`.

### Editable Installation & Registration
To validate and register the module's entry point with the local configuration and run environment during development, use the `register` command:
```bash
mirrordash-cli register ./mirrordash-<name>
```

### Starting the Server
Start the local server using the CLI `start` command to run the core MirrorDash application:
```bash
mirrordash-cli start
```

---

## 2. Coding Rules for Modules

### Async & Non-Blocking Loops
1. **Never block the event loop**: The module's `run_loop` is an async task. Do not use blocking operations (like `requests`, `urllib.request.urlopen`, or `time.sleep()`).
2. **Wrap Synchronous I/O**: Use `await asyncio.to_thread(sync_func, ...)` to offload synchronous network or disk reads.
3. **Use Async Sleeps**: Sleep only with `await asyncio.sleep(self.interval)`.
4. **Handle Shutdown Cleanly**: Always catch and re-raise `asyncio.CancelledError` to allow graceful stops:
   ```python
   except asyncio.CancelledError:
       # perform cleanup...
       raise
   ```

### State & Persistence (OverlayFS Compliance)
The system runs on a read-only root filesystem in production.
- **Do not write to package directories**: Never open files relative to `__file__` for writing.
- **Use Injected Paths**:
  - `self.data_dir`: Write SQLite databases, configurations, and user state here (backed up).
  - `self.cache_dir`: Write temporary data, HTTP response caches, and asset downloads here (excluded from backups).

---

## 3. Localization & Globals

### Respect Global Configurations
Never hardcode locales, metric units, or time zones. Fall back to settings defined under the global configuration:

```python
def __init__(self, config):
    global_cfg = config.get("globals", {})
    self.language = global_cfg.get("language", "en")
    self.timezone = global_cfg.get("timezone", "Europe/Stockholm")
    self.time_format = global_cfg.get("time_format", "24h")
    self.temp_unit = global_cfg.get("temperature_unit", "C")
```

### Localization Mappings
1. Place translation dictionaries in a `translations/` directory (e.g. `en.json`, `sv.json`) inside your package folder.
2. The core automatically resolves and merges `translations` onto the Jinja2 render context as `translations` and attaches them to `self.translations`.
3. Use the injected helper `self.translate("key", "default_val")` inside Python files.

---

## 4. UI Design & Styling Rules

All module designs must adhere to the MirrorDash **Ethereal Design System** to preserve visual unity on a dark ambient mirror display:

- **Transparent Backgrounds**: Widgets float on a pure black background. Never define a custom background color on the module wrapper.
- **HUD Contrast**: Use standard CSS custom properties for text and UI colors:
  - Primary text/numbers: `var(--color-primary-white)` or `#ffffff`
  - Secondary metadata/labels: `var(--color-secondary-grey)` or `#999999`
  - Dimmed borders/dividers: `var(--color-dimmed-charcoal)` or `#666666`
- **Vector Icons**: Use Lucide outline icons via standard HTML attributes. Do not use emoji icons:
  ```html
  <i data-lucide="cloud-rain"></i>
  ```
- **Translation-Safe Responsive Fluidity**:
  - **No fixed widths**: Do not use hardcoded pixel widths (`width: 150px`) for lists, columns, or layout elements. Swedish, German, or French text strings can be twice as long as English.
  - Use Flexbox or CSS Grid with flexible sizing (`flex: 1`, `min-width: 0`, `max-content`).
  - Use text-overflow ellipsis utilities to handle long strings gracefully.
- **Shadow DOM Encapsulation**: Remember that modules render inside Shadow DOM. All widget-specific CSS must reside inside a template `<style>` block. Global styles do not cascade in, and global scripts (`document.querySelector`) cannot select your module's elements. Query relative to the shadow root if client-side JS is needed.

---

## 5. Configuration UI (Admin Dashboard Integration)

Provide a `config_schema` dictionary or a `config_schema.json` to allow the user to modify settings from the Admin panel UI.

- Use basic JSON schema types (`boolean`, `string`, `integer`).
- Define title, description, and sensible default values.
- If providing a set of selections, use `enum` to render a dropdown.

---

## 6. Checklist for Module Commits
Before submitting a pull request or code change:
1. Ensure the package naming matches Hatchling requirements (folder uses hyphens, package/source uses underscores).
2. Ensure you have provided a `README.md` at the module root containing:
   - Clear description.
   - Step-by-step setup instructions for API keys/tokens (if any).
   - A `screenshot.png` at the package root, referenced in the markdown.
3. Run the test suite: `pytest tests/` (verify backend-to-module loading isn't broken).
