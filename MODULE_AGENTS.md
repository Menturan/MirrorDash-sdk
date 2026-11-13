# MODULE_AGENTS.md — MirrorDash Module AI Agent Guide

This file provides AI coding agents with instructions for creating, modifying, and testing custom modules for MirrorDash. Read this before developing any module.

---

## 1. Developer Environment & Scaffolding

### Always Use the CLI Scaffolder
Never build module packages by hand. Create the module, then delete the parts it doesn't need:
```bash
uvx mirrordash-sdk create-module mirrordash-<name> --description "<description>"
```
This gives the right Hatchling layout, entry point, settings form, translations and tests (`uv run pytest`), with every part a module can have, each marked `── <part> ──` in `plugin.py`, `widget.html` and the tests; the module's README lists each part's settings and texts. Delete a part with its settings, texts and tests, and keep the rest as it is written.

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
0. **Fetch with `self.fetch_json` / `self.fetch`**: never write your own HTTP code (`requests`, `httpx`, `urllib`, `aiohttp`); `validate` warns about it. `self.fetch_json` for JSON answers, `self.fetch` (bytes) for everything else (RSS, ICS, XML). Both take `headers=`, `params=`, `method=`, `json=`, `data=`, `timeout=` and return `(data, error)`: they have a timeout, don't block, pause while the screen is off, and on a failure return the last good answer with `error` set (`rejected`, `offline`, `http <code>`, `invalid`). Put API keys in `headers` or the body, never in the URL. An answer younger than `self.interval` is reused, so a restart (every saved setting) doesn't call again; pass `max_age=0` where a call must happen (an *Update now*). Never put the render time in the HTML: identical HTML isn't redrawn, changing HTML is. Show `data` when there is any and a `.module-message` when `error` is set. In tests: `module.fetch_json = AsyncMock(return_value=(data, None))`.
1. **Never block the event loop**: `render()` (and a module's own `run_loop`) run on the mirror's event loop. Do not use blocking operations (like `requests`, `urllib.request.urlopen`, or `time.sleep()`).
2. **Wrap Synchronous I/O**: Use `await asyncio.to_thread(sync_func, ...)` to offload synchronous network or disk reads.
3. **No loop unless you need one**: a module with `async def render()` and no `run_loop` is shown every `self.interval` seconds and at once after `self.changed.set()`. Write `run_loop` only for your own timing (a ticking clock, a stream, a time of day), and sleep there only with `await asyncio.sleep(...)`.
4. **Handle Shutdown Cleanly**: in your own `run_loop`, catch and re-raise `asyncio.CancelledError` to allow graceful stops:
   ```python
   except asyncio.CancelledError:
       # perform cleanup...
       raise
   ```

### State & Persistence (OverlayFS Compliance)
The system runs on a read-only root filesystem in production.
- **Do not write to package directories**: Never open files relative to `__file__` for writing.
- **Use the paths in `config`** (each instance has its own; no other folder is writable, and no other module's is readable):
  - `config["data_dir"]`: SQLite databases, configurations, and user state (backed up).
  - `config["cache_dir"]`: temporary data and asset downloads (excluded from backups). `fetch_json` caches its answers here by itself.

### The Sandbox
Every instance runs in a process of its own as a user of its own: no `sudo`, no home network except the addresses in `"format": "lan-url"` settings, I²C, SPI and sound playback (never a microphone; stop playing in `on_shown(False)`) but no GPIO chip (`gpiod`, `gpiozero` and `RPi.GPIO` don't work: ask for pins with `await self.gpio([27], output=True)`). The `event_bus` in `config` carries the mirror's hardware messages (`hardware.button`, `hardware.motion`, `hardware.climate`, `hardware.light`, `hardware.fan`); a module's own `publish` stays in its instance, unless `public=True`: then every instance gets it, named `<package>.<what>` (others are dropped), JSON up to 64 kB, 20 a second, readable by every module (no secrets). A class `router` (FastAPI `APIRouter`) is served at `config["api_path"]` without a login: check a secret yourself. Details: MODULE_GUIDE.md parts 3 and 9.

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
2. The mirror picks the file for its language (English for what is missing) and gives it to templates as `translations` and to Python as `self.translations`.
3. Use the injected helper `self.translate("key", "default_val")` inside Python files.

---

## 4. UI Design & Styling Rules

All module designs follow the mirror's design system (the component library at `/design`), so every module looks like part of one calm display:

- **Transparent Backgrounds**: Widgets float on a pure black background. Never define a custom background color on the module wrapper.
- **Full-screen layers**: in the `background` or `foreground` position (MirrorDash 0.12) the card is see-through and the mirror sets `--md-layer-size: 100%` on it; size with `width: var(--md-layer-size, 40vw)` so the same CSS fills the screen there and keeps a box elsewhere.
- **Component library first**: start every layout from `http://localhost:8000/design` and copy its markup; everything there works in a module except the parts marked "The mirror's own UI". The usual ones: `.module-header`, `.display-xl`/`.display-lg` (big numbers), `.data-list` (label–value rows), `.stats-grid`, `.forecast-grid`, `.agenda-list`, `.gauge-bar`, `.alert-callout`, `.module-message` (errors and empty states), `.flex-*`, `.text-*`. No CSS needed for these.
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
- **Avoid motion that never ends** (strongly advised against, not forbidden; the owner decides): an `infinite` CSS animation or a `requestAnimationFrame` loop redraws the whole screen 60 times a second all day and keeps the Pi hot; `validate` warns about both. It costs video too: while a video plays the mirror pauses CSS animations but not the module's JavaScript, and each redraw drops a video frame. A module that keeps moving anyway says so in its README and has a setting to turn the motion off or down. Between updates the card stands still; a ticker steps with `setInterval` and a short `transition`. Motion only while something loads, and it stops. A smooth scroll that must keep moving uses `steps()` with one whole pixel per step, no `mask-image` and `will-change: transform` (about a quarter of the cost; `validate` warns mildly).
- **Shadow DOM Encapsulation**: Remember that modules render inside Shadow DOM. CSS beyond the building blocks goes in a template `<style>` block; other page styles do not cascade in, and global scripts (`document.querySelector`) cannot select your module's elements. Every template `<script>` gets `root` (the module's shadow root): query from it and keep timers on it (`clearInterval(root._timer); root._timer = setInterval(...)`). Never use `document.currentScript` (null in a shadow root) or globals (two instances would share them).

---

## 5. Configuration UI (Admin Dashboard Integration)

Provide a `config_schema.json` next to `plugin.py` to allow the user to modify settings from the Admin panel UI. The core reads it as a file and never imports the module, so a `config_schema` in the class isn't read.

- The `type` picks the box, the `format` changes it; never the key's name. The table in MODULE_GUIDE part 6 and `/design#forms` show every one.
- Define title, description and a default for every setting: the mirror hands the module each default until the owner saves another (MirrorDash 0.14), so read `config["key"]` and don't repeat the default in code.
- If providing a set of selections, use `enum` with `enum_titles` (the words the owner reads) to render a dropdown.
- A slider is `"format": "slider"` with `minimum` and `maximum`; without the format those two are rules on a number box (MirrorDash 0.14).
- A setting for one choice only gets `"show_if": {"source": ["immich"]}`; settings out of the way get `"group": "Advanced"`. Prefer them to a nested object (MirrorDash 0.14).
- Run `mirrordash-sdk validate`: it warns about unknown keywords and formats, an enum without titles and a setting without a default.
- API keys, tokens and passwords get `"format": "password"`, so the admin page hides what is typed (`mirrordash-sdk validate` warns otherwise).
- An address on the home network (Home Assistant, a device) gets `"format": "lan-url"`: the module runs sandboxed and reaches the home network only at such addresses.
- Choices that come from outside the module (schools, calendars, places) get `"type": "object"` with `"format": "list"` (a dropdown) or `"search"` (suggestions while typing) and an `async def settings_list_<key>(self, item)` / `settings_search_<key>(self, item, query)` returning `[{"id", "name", "detail"}]`; saved as `{"id", "name"}`. Keys a-z, 0-9 and `_`; `raise ValueError("…")` shows its text under the field (MirrorDash 0.13; MODULE_GUIDE part 6).
- The admin page is English only: titles, descriptions and those errors in English; `translations/` are for the mirror.
- Rules on what the owner types are plain JSON Schema keywords: `required` (beside `properties`, and in a list setting's `items`), `minimum`/`maximum`, `minLength`/`maxLength`, `pattern` (matches the whole value) with `pattern_message` (the words for the owner). The browser and the save check them (MirrorDash 0.13).
- A Lucide icon name gets `"format": "icon"`: the admin page suggests names as the owner types and draws the icon (MirrorDash 0.11.0; older shows a text field).
- Files the owner uploads (photos) get `"format": "files"` with `"accept": "image"` (no `type`, no `default`); nothing goes into `config`, the module reads them from its cache folder (MirrorDash 0.12).
- Don't declare `instance_name`, `enabled`, `position`, `carousel_group`, `carousel_interval`, `max_width`, `max_height`, `z_index`, `opacity`, `show_in_privacy` or `schedule`: the core adds them to every module.
- `self.render_template` / `self.translate` don't exist yet inside `__init__`; use them from `render` or `run_loop`.

---

## 6. Checklist for Module Commits
Before submitting a pull request or code change:
1. Ensure the package naming matches Hatchling requirements (folder uses hyphens, package/source uses underscores).
2. Ensure you have provided a `README.md` at the module root containing:
   - Clear description.
   - Step-by-step setup instructions for API keys/tokens (if any).
   - A `screenshot.png` at the repository root, referenced in the README (GitHub shows it; the mirror shows the repository's "About" text).
3. Keep `<package>/preview/` current: `fixtures.json` (`{"captured": "<date>", "answers": {"<host/path pattern>": "<file>"}}`) and a made-up sample answer for every address `render()` fetches, so the admin page's preview shows real-looking data (MODULE_GUIDE.md, *Sample answers for the preview*). No keys, no copied third-party text; `{"answers": {}}` for a module that fetches nothing.
4. Run the test suite: `uv run pytest`, and `uvx mirrordash-sdk validate .`.
5. Share through GitHub only: commit, then `uvx mirrordash-sdk release X.Y.Z`, which sets the `pyproject.toml` version, tags `vX.Y.Z`, pushes, makes the GitHub Release and sets the `mirrordash-module` topic on the repository (a mirror lists only `mirrordash-*` repositories with that topic). Don't publish modules to PyPI; mirrors install from the Git URL and need the release.
