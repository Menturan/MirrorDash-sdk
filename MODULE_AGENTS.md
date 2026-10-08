# MODULE_AGENTS.md — MirrorDash Module AI Agent Guide

This file provides AI coding agents with instructions for creating, modifying, and testing custom modules for MirrorDash. Read this before developing any module.

---

## 1. Developer Environment & Scaffolding

### Always Use the CLI Scaffolder
Never build module packages by hand. Create a module from a template; pick `api` when it fetches data from a web API, `basic` otherwise:
```bash
uvx mirrordash-sdk create-module mirrordash-<name> --template api --description "<description>"
```
This gives the right Hatchling layout, entry point, settings form, translations and tests (`uv run pytest`).

### A Local Mirror
Inside the module directory, set up a local mirror with the module on it and start it (`http://localhost:8000/`, admin password `mirrordash`):
```bash
uvx mirrordash-sdk dev-setup -e
uvx mirrordash-sdk start
```
`uvx mirrordash-sdk quickstart mirrordash-<name>` does all of the above in one go and opens the browser.

---

## 2. Coding Rules for Modules

### Async & Non-Blocking Loops
0. **Fetch with `self.fetch_json`**: never write your own HTTP code for JSON APIs. `data, error = await self.fetch_json(url, headers=..., params=...)` has a timeout, doesn't block, and on a failure returns the last good answer with `error` set (`rejected`, `offline`, `http <code>`, `invalid`). Put API keys in `headers`, never in the URL. Show `data` when there is any and a `.module-message` when `error` is set. In tests: `module.fetch_json = AsyncMock(return_value=(data, None))`.
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
- **Building blocks first**: lay out with the classes every module gets (no CSS needed): `.module-header`, `.display-xl`/`.display-lg` for big numbers, `.flex-row`, `.flex-row-between` (label–value rows), `.flex-column`, `.text-primary`/`.text-secondary`, `.module-message` for errors and empty states. See `http://localhost:8000/design`.
- **HUD Contrast**: For your own CSS, use the design tokens:
  - Primary text/numbers: `var(--color-high-contrast)` (#ffffff)
  - Secondary metadata/labels: `var(--color-standard-gray)` (#999999)
  - Dimmed borders/dividers: `var(--color-dimmed-charcoal)` (#666666)
- **Vector Icons**: Use Lucide outline icons via standard HTML attributes. Do not use emoji icons:
  ```html
  <i data-lucide="cloud-rain"></i>
  ```
- **Translation-Safe Responsive Fluidity**:
  - **No fixed widths**: Do not use hardcoded pixel widths (`width: 150px`) for lists, columns, or layout elements. Swedish, German, or French text strings can be twice as long as English.
  - Use Flexbox or CSS Grid with flexible sizing (`flex: 1`, `min-width: 0`, `max-content`).
  - Use text-overflow ellipsis utilities to handle long strings gracefully.
- **Shadow DOM Encapsulation**: Remember that modules render inside Shadow DOM. CSS beyond the building blocks goes in a template `<style>` block; other page styles do not cascade in, and global scripts (`document.querySelector`) cannot select your module's elements. Every template `<script>` gets `root` (the module's shadow root): query from it and keep timers on it (`clearInterval(root._timer); root._timer = setInterval(...)`). Never use `document.currentScript` (null in a shadow root) or globals (two instances would share them).

---

## 5. Configuration UI (Admin Dashboard Integration)

Provide a `config_schema` dictionary or a `config_schema.json` to allow the user to modify settings from the Admin panel UI.

- Use basic JSON schema types (`boolean`, `string`, `integer`).
- Define title, description, and sensible default values.
- If providing a set of selections, use `enum` to render a dropdown.
- API keys, tokens and passwords get `"format": "password"`, so the admin page hides what is typed (`mirrordash-sdk validate` warns otherwise).
- Don't declare `enabled`, `position`, `carousel_group`, `carousel_interval`, `max_width`, `max_height`, `z_index` or `opacity`: the core adds them to every module.
- `self.render_template` / `self.translate` don't exist yet inside `__init__`; use them from `run_loop`.

---

## 6. Checklist for Module Commits
Before submitting a pull request or code change:
1. Ensure the package naming matches Hatchling requirements (folder uses hyphens, package/source uses underscores).
2. Ensure you have provided a `README.md` at the module root containing:
   - Clear description.
   - Step-by-step setup instructions for API keys/tokens (if any).
   - A `screenshot.png` at the package root, referenced in the markdown.
3. Run the test suite: `uv run pytest`, and `uvx mirrordash-sdk validate .`.
