# Build a MirrorDash module

A **module** is one small panel on the mirror: the time, the weather, your calendar. You write it in
Python and HTML. Python decides *what* to show (for example, fetches the weather), and a small HTML file
decides *how* it looks.

This guide takes you from nothing to a finished module you can share. Part 1 and 2 are a hands-on
tutorial; the rest is reference you can come back to.

**You need:** basic Python (functions, classes, dictionaries), a terminal, and
[uv](https://docs.astral.sh/uv/getting-started/installation/) (a tool that installs Python packages).
For sharing your module at the end, you also need a GitHub account. Words in *italics* are explained in
[Words used in this guide](#words-used-in-this-guide) at the end.

## Contents

1. [Your first module (5 minutes)](#1-your-first-module-5-minutes)
2. [Tutorial: show the weather outside](#2-tutorial-show-the-weather-outside)
3. [How a module works](#3-how-a-module-works)
4. [Design: the component library](#4-design-the-component-library)
5. [Fetching data](#5-fetching-data)
6. [Settings](#6-settings)
7. [Translations](#7-translations)
8. [Saving files](#8-saving-files)
9. [Hardware and other modules](#9-hardware-and-other-modules)
10. [Testing](#10-testing)
11. [Sharing your module](#11-sharing-your-module)
12. [Troubleshooting](#12-troubleshooting)
13. [Reference: what the mirror gives your module](#13-reference-what-the-mirror-gives-your-module)
14. [Words used in this guide](#words-used-in-this-guide)

---

## 1. Your first module (5 minutes)

Open a terminal in the folder where you keep your projects and run:

```bash
uvx mirrordash-sdk quickstart mirrordash-outside
```

This one command:

1. creates the folder `mirrordash-outside` with a working module in it,
2. sets up a small MirrorDash mirror on your computer (in `mirrordash-outside/.venv`),
3. adds your module to that mirror,
4. starts the mirror and opens it in your browser at `http://localhost:8000/`.

**You should see:** a panel with the title **OUTSIDE**, a big **21**, the rows **Min 18** and **Max 24**,
and the line *"Example data. Add an API key in the module's settings."* That is your module, showing
example data.

Good to know:

- **Stop the mirror** with `Ctrl+C` in the terminal. **Start it again** from the module's folder:
  ```bash
  cd mirrordash-outside
  uvx mirrordash-sdk start
  ```
- **Changes show up by themselves.** While the mirror runs, save a file in the module and the mirror
  restarts and shows the change after a few seconds. You don't need to reload the browser.
- **The admin page** of your local mirror is at `http://localhost:8000/admin`, password `mirrordash`.
  That's where users change your module's settings.
- **The component library** is at `http://localhost:8000/design`: every building block you can use for
  the look, with code to copy. More in [part 4](#4-design-the-component-library).

---

## 2. Tutorial: show the weather outside

In six small steps you turn the example into a real module that shows the temperature, wind and humidity
outside. Keep the mirror running (part 1) and the browser open next to your editor. After each step,
save and look at the browser.

The files you will change are in `mirrordash-outside/mirrordash_outside/`.

### Step 1: Change the title

Open `mirrordash_outside/translations/en.json`. It holds the texts your module shows, in English. Change
the title:

```json
"title": "Outside",
```

(Leave the other lines as they are.)

**You should see:** nothing new yet, the title was already "Outside". Try `"Weather outside"` instead,
save, and watch the title change. Then change it back to `"Outside"`.

### Step 2: Fetch real data

The example data comes from `plugin.py`. Now it should fetch real weather from
[Open-Meteo](https://open-meteo.com), a free weather service that needs no API key. Replace everything
in `mirrordash_outside/plugin.py` with:

```python
import asyncio
import logging

logger = logging.getLogger("mirrordash.modules.mirrordash_outside")

# Open-Meteo: free weather data, no API key needed (https://open-meteo.com)
URL = "https://api.open-meteo.com/v1/forecast"


def parse(data: dict, show_wind: bool) -> dict:
    """Pick what to show from Open-Meteo's answer: one big value and a few rows."""
    now = data["current"]
    rows = [("Humidity", f"{now['relative_humidity_2m']} %")]
    if show_wind:
        rows.insert(0, ("Wind", f"{now['wind_speed_10m']} km/h"))
    return {"value": f"{round(now['temperature_2m'])}°", "rows": rows}


class OutsideModule:
    # Keeps pytest from collecting this class as a test
    __test__ = False

    def __init__(self, config):
        self.config = config
        self.name = "mirrordash_outside"
        self.interval = config.get("interval", 600)
        self.show_wind = config.get("show_wind", True)  # a setting you add in step 4
        # Where the mirror is: set once for the whole mirror, under Settings in the admin page
        self.latitude = config.get("globals", {}).get("latitude", 59.33)
        self.longitude = config.get("globals", {}).get("longitude", 18.07)

    async def run_loop(self, broadcast_func):
        """Runs as long as the mirror does: fetch, show, wait, repeat."""
        while True:
            try:
                await broadcast_func(self.name, await self.render())
            except asyncio.CancelledError:
                raise  # the mirror is stopping this module: let it
            except Exception as e:
                logger.error(f"{self.name}: {e}", exc_info=True)
            await asyncio.sleep(self.interval)

    async def render(self) -> str:
        data, error = await self.fetch_json(URL, params={
            "latitude": self.latitude,
            "longitude": self.longitude,
            "current": "temperature_2m,wind_speed_10m,relative_humidity_2m",
        })
        message = self.translate("fetch_failed", "Couldn't update.") if error else None
        shown = parse(data, self.show_wind) if data else None
        return self.render_template("widget.html", data=shown, message=message, icon="cloud-off")
```

What it does, from the bottom up:

- `render()` asks Open-Meteo for the current weather with `self.fetch_json` (a helper the mirror gives
  every module, see [part 5](#5-fetching-data)), turns the answer into what to show with `parse()`, and
  fills in `templates/widget.html` with it.
- `run_loop()` runs as long as the mirror does: it shows the result, waits `interval` seconds (600 = 10
  minutes), and starts over. `broadcast_func` is how you send the result to the screen.
- `__init__()` reads the module's settings from `config`. The mirror's own location (latitude and
  longitude) comes from the mirror's global settings.

The example also had a setting for an API key, which this module doesn't need. Replace everything in
`mirrordash_outside/config_schema.json` with:

```json
{
  "title": "Outside",
  "description": "The weather outside, right now.",
  "type": "object",
  "properties": {
    "interval": {
      "type": "integer",
      "default": 600,
      "title": "Update Interval (Seconds)",
      "description": "Time between updates."
    },
    "show_header": {
      "type": "boolean",
      "default": true,
      "title": "Show Header",
      "description": "Show or hide the module's title."
    }
  }
}
```

**You should see:** the real temperature outside (in Stockholm, the default location), with
**Wind** and **Humidity** below it. The example-data line is gone.

### Step 3: Change the look with the component library

The rows are a *data list*. Let's show wind and humidity side by side instead, as a *stats grid*:

1. Open `http://localhost:8000/design` and scroll to **Extended Layout Elements → Stats Grid**. That's
   the look we want.
2. Its code shows the pattern: a `stats-grid` with one `stats-grid__item` per value.

Replace everything in `mirrordash_outside/templates/widget.html` with:

```html
<div class="flex-column">
    {% if show_header %}
    <h2 class="module-header">{{ translations.get("title", "Outside") }}</h2>
    {% endif %}
    {% if data %}
    <span class="display-lg">{{ data.value }}</span>
    <div class="stats-grid">
        {% for label, value in data.rows %}
        <div class="stats-grid__item">
            <span class="stats-grid__value">{{ value }}</span>
            <span class="stats-grid__label">{{ label }}</span>
        </div>
        {% endfor %}
    </div>
    {% endif %}
    {% if message %}
    <div class="module-message"><i data-lucide="{{ icon }}"></i><span>{{ message }}</span></div>
    {% endif %}
</div>
```

The `{{ ... }}` and `{% ... %}` parts are *Jinja*: `{{ data.value }}` puts in a value from Python, and
`{% if %}` / `{% for %}` show parts only when needed or once per row.

**You should see:** the temperature, and wind and humidity next to each other underneath.

### Step 4: Add a setting

Users should be able to turn the wind off. Settings are described in `config_schema.json`; the admin
page builds a form from it. Add a `show_wind` setting: replace everything in
`mirrordash_outside/config_schema.json` with:

```json
{
  "title": "Outside",
  "description": "The weather outside, right now.",
  "type": "object",
  "properties": {
    "show_wind": {
      "type": "boolean",
      "default": true,
      "title": "Show Wind",
      "description": "Show the wind speed."
    },
    "interval": {
      "type": "integer",
      "default": 600,
      "title": "Update Interval (Seconds)",
      "description": "Time between updates."
    },
    "show_header": {
      "type": "boolean",
      "default": true,
      "title": "Show Header",
      "description": "Show or hide the module's title."
    }
  }
}
```

`plugin.py` already reads it: `self.show_wind = config.get("show_wind", True)`.

Now try it as a user would:

1. Open `http://localhost:8000/admin` and log in with `mirrordash`.
2. Open **Modules**, find **Outside** and press **Configure**.
3. Under **Module Settings**, turn **Show Wind** off, then press **Save Configuration** at the bottom.

**You should see:** the mirror shows only the humidity. Turn it on again and the wind comes back.

### Step 5: Run the tests

Tests check that your module still works after a change, without starting the mirror. Replace everything
in `tests/test_plugin.py` (in the module's main folder, next to `pyproject.toml`) with:

```python
from unittest.mock import AsyncMock, MagicMock

import pytest

from mirrordash_outside.plugin import OutsideModule, parse

ANSWER = {"current": {"temperature_2m": 13.8, "wind_speed_10m": 14.8, "relative_humidity_2m": 79}}


def make_module(**settings):
    """The module as the mirror sets it up, with the mirror's helpers replaced by fakes."""
    module = OutsideModule(settings)
    module.render_template = MagicMock(side_effect=lambda name, **context: context)  # returns what the template gets
    module.translate = lambda key, default=None: default
    module.fetch_json = AsyncMock(return_value=(ANSWER, None))
    return module


def test_parse_rounds_the_temperature_and_can_leave_out_the_wind():
    assert parse(ANSWER, show_wind=True) == {"value": "14°", "rows": [("Wind", "14.8 km/h"), ("Humidity", "79 %")]}
    assert parse(ANSWER, show_wind=False)["rows"] == [("Humidity", "79 %")]


@pytest.mark.asyncio
async def test_shows_the_weather():
    shown = await make_module().render()
    assert shown["data"]["value"] == "14°"
    assert shown["message"] is None


@pytest.mark.asyncio
async def test_says_so_when_it_cant_update():
    module = make_module()
    module.fetch_json.return_value = (None, "offline")
    shown = await module.render()
    assert shown["data"] is None
    assert shown["message"] == "Couldn't update."
```

Then, in the module's folder:

```bash
uv run pytest
```

**You should see:** `3 passed`. Break something on purpose (for example, change `round(` to `int(` in
`parse()`), run the tests again and see one fail. Change it back.

### Step 6: Share it

Check the module, then follow [part 11](#11-sharing-your-module) to put it on GitHub:

```bash
uvx mirrordash-sdk validate .
```

**You should see:** `STATUS: PASS WITH WARNINGS`. The only warning is the missing `screenshot.png`; take
a screenshot of your module in the browser and save it as `screenshot.png` in the module's folder.

You've built a real module. The rest of this guide explains each part in more detail.

---

## 3. How a module works

A module made with `create-module` or `quickstart` looks like this:

```
mirrordash-outside/                  the module's folder (and later its GitHub repository)
├── pyproject.toml                   name, version, and how the mirror finds the module
├── README.md                        what it does and how to set it up, for users
├── mirrordash_outside/              the module's code
│   ├── plugin.py                    Python: what to show, and when
│   ├── templates/widget.html        HTML: how it looks
│   ├── config_schema.json           its settings in the admin page
│   ├── translations/en.json         its texts (sv.json etc. for other languages)
│   └── icon.svg                     its icon in the admin page
└── tests/test_plugin.py             its tests
```

**What happens when the mirror starts:**

1. The mirror finds your module through the *entry point* in `pyproject.toml` (`create-module` writes it
   for you).
2. It creates your class: `OutsideModule(config)`. `config` holds the module's settings.
3. It gives the object a few helpers: `self.render_template`, `self.translate` and `self.fetch_json`.
   They don't exist yet inside `__init__`, so use them from `run_loop`.
4. It starts `run_loop(broadcast_func)`, which runs as long as the mirror does. Each time it has
   something new to show, it calls `await broadcast_func(self.name, html)`.

**`async` and `await`:** the mirror runs all modules at the same time. `async def` marks a function that
can wait without blocking the others, and `await` is where it waits: for data (`await self.fetch_json(...)`),
for the screen (`await broadcast_func(...)`) or for time (`await asyncio.sleep(...)`). Never use
`time.sleep()` or `requests`: they block the whole mirror.

**When `run_loop` stops and starts again:**

- When the user changes a setting, the mirror stops every module and creates them again with the new
  settings. That's why you read settings in `__init__`.
- If `run_loop` crashes, the mirror logs the error and starts it again after 5 seconds, then 10, 20 and
  so on, at most every 5 minutes. Catch errors inside the loop (as the tutorial does) so one bad answer
  doesn't stop the module.
- When the mirror stops, `run_loop` gets an `asyncio.CancelledError`. Let it through with
  `except asyncio.CancelledError: raise` (`mirrordash-sdk validate` checks for it).

---

## 4. Design: the component library

**Start every design at `http://localhost:8000/design`** (while your local mirror runs). It's the
mirror's component library: every building block, how it looks, and the HTML to copy. Everything there
works in your module, except the parts marked *"The mirror's own UI"*.

How to use it:

1. Find a component that looks like what you want to show.
2. Press **Copy** and paste the code into `templates/widget.html`.
3. Replace the example texts with your values: `{{ data.value }}`, or `{% for %}` for one row per item.

The most useful components:

| Component | Use it for |
| :--- | :--- |
| `module-header` | The module's title, at the top. Wrap it in `{% if show_header %}` so users can hide it. |
| `display-xl`, `display-lg` | One big number: a time, a temperature. |
| `data-list` | Rows with a label on the left and a value on the right. Can show up/down values in color. |
| `stats-grid` | Two or three values side by side, each with a small label. |
| `forecast-grid` | Days in a row, each with a name, an icon and a value (a weather forecast). |
| `agenda-list` | Things that happen on a date: calendar events, deliveries. |
| `gauge-bar` | How full something is, as a bar: a battery, a download. |
| `alert-callout` | A warning that must stand out. |
| `status-indicator` | A small green or red dot: online or not. |
| `module-message` | A quiet line with an icon: "Couldn't update", "Nothing today", "Add an API key". |
| `flex-row`, `flex-column`, `flex-row-between` | Putting things next to or under each other. |
| `text-primary`, `text-secondary`, `text-dimmed` | White, gray and dark gray text. |

**Icons:** find one at [lucide.dev/icons](https://lucide.dev/icons) and use its name:
`<i data-lucide="cloud-rain"></i>`. The mirror draws it.

**Rules for the mirror's look** (the component library already follows them):

- **No background color** on your module: it floats on the black mirror.
- **No fixed widths** like `width: 150px` on text: Swedish or German words are often longer than English.
- The mirror's browser is **WebKit** (like Safari), not Chrome. Plain HTML, CSS and JavaScript work; avoid
  brand-new or Chrome-only features.

**When the library isn't enough:** add a `<style>` block to `widget.html`. Your styles only affect your
module, because each module lives in its own *shadow DOM*: styles from outside don't get in, and yours
don't get out. Use the mirror's colors through its variables, for example
`color: var(--color-high-contrast)` (white), `var(--color-standard-gray)` (gray) or
`var(--color-dimmed-charcoal)` (dark gray).

**JavaScript:** a `<script>` in `widget.html` gets a variable `root`: your module's own part of the page.
Find your elements with `root.querySelector(...)`, not `document.querySelector(...)` (which can't see
inside your module). The script runs again each time you broadcast new HTML, so keep timers on `root`:

```html
<div class="display-xl clock"></div>
<script>
  const el = root.querySelector('.clock');
  clearInterval(root._timer);  // stop the timer from the previous update
  root._timer = setInterval(() => { el.textContent = new Date().toLocaleTimeString(); }, 1000);
</script>
```

---

## 5. Fetching data

Use `self.fetch_json` for any web *API* that answers in JSON. It has a timeout, doesn't block the
mirror, and remembers the last good answer, so the module keeps showing data when the internet is gone,
even after a restart.

```python
data, error = await self.fetch_json(
    "https://api.example.com/v1/current",
    headers={"Authorization": f"Bearer {self.config['api_key']}"},  # an API key goes in a header
    params={"q": "Stockholm"},                                       # becomes ?q=Stockholm
    timeout=10,
)
```

It always gives back two things: `data` (the answer) and `error` (what went wrong, or `None`).

| `error` | Meaning | `data` |
| :--- | :--- | :--- |
| `None` | It worked. | The answer. |
| `"rejected"` | The service said no (401/403): usually a wrong or missing API key. | The last good answer, or `None`. |
| `"offline"` | No answer: no internet, the service is down, or it took too long. | The last good answer, or `None`. |
| `"http <code>"` | Another error from the service, for example `"http 429"`: too many requests. | The last good answer, or `None`. |
| `"invalid"` | The answer wasn't JSON. | The last good answer, or `None`. |

- **Show what you have, and say what's wrong:** show `data` when there is any, and a `module-message` when
  `error` is set, like the tutorial does.
- **API keys go in `headers`, never in the URL.** The mirror never writes headers to its log, so the key
  stays secret. Most APIs say in their documentation which header they want (`Authorization`,
  `X-Api-Key`, …). Let the user enter the key as a setting (see [part 6](#6-settings)).
- **No retries:** a failed fetch is simply tried again at the next `interval`. Keep the interval within
  what the service allows; free APIs often allow a request every few minutes.
- **Need an API key to start with?** `uvx mirrordash-sdk create-module mirrordash-x --template api`
  gives you a module that already has an API key setting, example data until a key is entered, and
  messages for every error.

---

## 6. Settings

`config_schema.json` describes your module's settings. The admin page builds a form from it, and your
module gets the values in `config` (read them in `__init__`):

```json
{
  "title": "Outside",
  "description": "The weather outside, right now.",
  "type": "object",
  "properties": {
    "city":    { "type": "string",  "default": "Stockholm", "title": "City", "description": "Which city to show." },
    "api_key": { "type": "string",  "default": "", "format": "password", "title": "API Key", "description": "Your key from the service." },
    "show_wind": { "type": "boolean", "default": true, "title": "Show Wind", "description": "Show the wind speed." }
  }
}
```

```python
self.city = config.get("city", "Stockholm")
```

- `title` at the top is the module's name in the admin page ("Outside", not "Outside Module Settings");
  `description` is the line under it.
- Each setting has a `type` (`string`, `integer`, `number`, `boolean`), a `default`, a `title` and a
  `description`.
- **Every kind of field** (text, number, switch, slider, dropdown, list, color, password, …) is shown
  with its JSON in the component library: `http://localhost:8000/design#forms`.
- **Secrets** (API keys, tokens, passwords) get `"format": "password"`, so the admin page hides what is
  typed. `mirrordash-sdk validate` warns if you forget.
- **Don't add these yourself:** `enabled`, `position`, `carousel_group`, `carousel_interval`,
  `max_width`, `max_height`, `z_index` and `opacity`. The mirror adds them to every module's form.
- When the user changes a setting, the mirror restarts your module with the new values.

**The mirror's global settings** are the same for all modules. Use them instead of asking the user again:

```python
place = config.get("globals", {})
latitude = place.get("latitude", 59.33)
```

| Key | Example | Meaning |
| :--- | :--- | :--- |
| `language` | `"sv"` | The mirror's language. |
| `timezone` | `"Europe/Stockholm"` | Its time zone. |
| `time_format` | `"24h"` or `"12h"` | How to show times. |
| `temperature_unit` | `"C"` or `"F"` | Celsius or Fahrenheit. |
| `distance_unit` | `"km"` or `"miles"` | Kilometres or miles. |
| `latitude`, `longitude` | `59.3293`, `18.0686` | Where the mirror is. |

---

## 7. Translations

Put your module's texts in `translations/en.json` (English, always needed) and, if you like, other
languages next to it (`sv.json` for Swedish, `de.json` for German):

```json
{ "title": "Outside", "fetch_failed": "Couldn't update." }
```

The mirror picks the file for its language and falls back to English for anything missing.

- **In `widget.html`:** `{{ translations.get("title", "Outside") }}`
- **In Python:** `self.translate("fetch_failed", "Couldn't update.")`

The second value is used when the text is in no file at all.

---

## 8. Saving files

The mirror's system files can't be written to (it protects its SD card). Never write files next to your
code. Use the two folders the mirror gives you:

| `config` key | What it's for | Kept in backups? |
| :--- | :--- | :--- |
| `config.get("data_dir")` | Things to keep: saved state, a small database. | Yes |
| `config.get("cache_dir")` | Things you can download again: images, temporary files. | No |

```python
import os

self.data_dir = config.get("data_dir")
self.state_file = os.path.join(self.data_dir, "state.json")
```

Each copy of your module (a user can add the same module twice) gets its own folders.
`self.fetch_json` already keeps its answers in `cache_dir`, so you don't need to.

---

## 9. Hardware and other modules

Modules can send each other messages through the mirror's *event bus*, and the mirror sends messages
about connected hardware the same way. You get the bus in `config`:

```python
class RoomModule:
    def __init__(self, config):
        event_bus = config.get("event_bus")
        if event_bus:
            event_bus.subscribe("hardware.climate", self.on_climate)  # call on_climate for each message

    def on_climate(self, data):
        self.temperature = data["temperature_c"]
```

Send your own messages with `event_bus.publish("mymodule:update", {"value": 21})`. Start the names with
your module's name so they don't clash. Subscribe in `__init__`: when settings change, all subscriptions
are cleared and every module is created again. A subscriber can be a normal function or an `async def`.

**Hardware messages** (only sent if the user connected the device under **Admin → Hardware → Sensors &
Inputs**):

| Message | Data | When |
| :--- | :--- | :--- |
| `hardware.button` | `{"press": "single" \| "double" \| "triple" \| "long", "action": "…", "button": "button" \| "button_2" \| "button_3" \| "button_4"}` | On every press. `action` is what the user chose for that press (already carried out); `button` says which of up to four buttons it was. |
| `hardware.motion` | `{"motion": true \| false, "sensor": "pir" \| "mmwave"}` | When someone comes or goes. |
| `hardware.climate` | `{"temperature_c": 21.5, "humidity": 40}` | Every 30 s. Always °C; convert with the `temperature_unit` global setting. |
| `hardware.light` | `{"lux": 250.0}` | Every 30 s. |
| `hardware.fan` | `{"level": 2, "max_level": 4, "cpu_temperature_c": 62.5}` | Every 30 s. `level` 0 is off. |

---

## 10. Testing

Tests check your module without starting the mirror. Run them in the module's folder:

```bash
uv run pytest
```

The mirror's helpers don't exist in a test, so replace them with fakes, as the tutorial's test does:

```python
module.render_template = MagicMock(side_effect=lambda name, **context: context)  # see what the template gets
module.translate = lambda key, default=None: default
module.fetch_json = AsyncMock(return_value=({"current": {...}}, None))           # a pretend answer
```

Test `async` functions with `@pytest.mark.asyncio` and `await` (the module's `pyproject.toml` already
has `pytest-asyncio`). Test the parts that make decisions: what you pick from the answer, and what you
show when something fails.

Before you share the module, check it:

```bash
uvx mirrordash-sdk validate .
```

It checks the files, the entry point, the settings and the README, and says what to fix.

---

## 11. Sharing your module

A module is shared through GitHub. Every mirror can install it from there, and finds it by itself.

1. **Name the repository `mirrordash-<name>`**, for example `mirrordash-outside`, and make it public.
   Mirrors search GitHub for that prefix.
2. **Write a short description** in the repository's **About** box on GitHub (the gear next to
   "About"). The mirror's module list shows it.
3. **Create the repository on GitHub** (empty: no README or license), then save your work and push it
   from the module's folder (`create-module` already made it a Git repository). The first time you use
   Git on this computer, tell it who you are:
   ```bash
   git config --global user.name "Your Name"
   git config --global user.email "you@example.com"
   ```
   Then:
   ```bash
   git add .
   git commit -m "First version"
   git remote add origin https://github.com/<you>/mirrordash-outside.git
   git push -u origin HEAD
   ```
4. **Make a release**, from the module's folder:
   ```bash
   uvx mirrordash-sdk release 0.1.0
   ```
   It checks the module, runs its tests, asks you to confirm, then tags the version `v0.1.0`, pushes it
   and makes the **GitHub Release**. That last step needs the [`gh`](https://cli.github.com/) tool
   (log in once with `gh auth login`); without it, the command prints a link where you press
   **Publish release**.

Now your module shows up under **Modules** in every mirror's admin page, and anyone can install it with
one click. They can also paste its address (`git+https://github.com/<you>/mirrordash-outside.git`)
under **Modules → Install a Module from GitHub**.

> [!IMPORTANT]
> **Without a GitHub Release, mirrors can't see or install the module.** They always install the newest
> release, not what's on your main branch.

**A new version:** commit your changes, then `uvx mirrordash-sdk release 0.1.1`. It sets `version` in
`pyproject.toml` to the same number as the tag, so the mirror shows the version you released. Mirrors
offer the update on the module's card. (`--dry-run` shows what it would do without changing anything.)

**The README** is the user's manual. It should say what the module shows, step by step how to get any
API key it needs and where to enter it, and show a `screenshot.png` (GitHub shows it on the module's
page).

---

## 12. Troubleshooting

**Where are the logs?** In the terminal where the mirror runs, and in the admin page under **Logs**.
Errors from your module start with its name, for example `mirrordash.modules.mirrordash_outside`.

| Problem | Why | What to do |
| :--- | :--- | :--- |
| The module doesn't show at all. | It isn't added to the mirror, or it's turned off. | In the module's folder run `uvx mirrordash-sdk dev-setup -e`. Check **Admin → Modules** that it's turned on. |
| The panel says "Loading …" or shows old content, and `Failed to render template` is in the log. | A mistake in `widget.html`, for example a `{% if %}` without `{% endif %}`. | The log line says which line; fix it and save. |
| The panel says "Loading …" or shows old content, and another error is in the log. | `plugin.py` crashed, for example on a key the answer doesn't have. | Read the error in the log; it names the file and line. The mirror tries again by itself. |
| A change doesn't show. | The mirror runs without watching for changes. | Start it with `uvx mirrordash-sdk start` from the module's folder. |
| An icon is missing. | The icon name doesn't exist. | Check the name at [lucide.dev/icons](https://lucide.dev/icons). |
| `fetch_json` gives `"rejected"`. | The service doesn't accept the API key. | Check the key, and which header the service wants it in. |
| `fetch_json` gives `"http 429"`. | Too many requests. | Raise `interval`. |
| The mirror shows "set an admin password". | The local mirror has no admin password. | Run `uvx mirrordash-sdk dev-setup` once; it sets `mirrordash`. |
| `uv run pytest` can't find your module. | You're not in the module's folder. | `cd` to the folder with `pyproject.toml` and run it again. |

---

## 13. Reference: what the mirror gives your module

**In `config`** (the argument to `__init__`):

| Key | What it is |
| :--- | :--- |
| your settings | Everything from `config_schema.json`, with the user's values. |
| `"globals"` | The mirror's global settings (language, time zone, units, location). See [part 6](#6-settings). |
| `"data_dir"` | A folder for things to keep. See [part 8](#8-saving-files). |
| `"cache_dir"` | A folder for things that may be thrown away. |
| `"translations"` | The module's texts in the mirror's language. Usually you use `self.translate` instead. |
| `"event_bus"` | Messages between modules, and from hardware. See [part 9](#9-hardware-and-other-modules). |

**On `self`** (added after `__init__`, so use them from `run_loop`):

| Helper | What it does |
| :--- | :--- |
| `self.render_template("widget.html", **values)` | Fills in a template from `templates/` and gives back the HTML. The template also gets `translations` and `show_header`. |
| `self.translate("key", "default")` | A text from `translations/`. |
| `await self.fetch_json(url, headers=…, params=…, timeout=10)` | Fetches JSON; gives back `(data, error)`. See [part 5](#5-fetching-data). |

**`await broadcast_func(self.name, html)`** puts `html` in your module's place on the screen.

`fetch_json` and the component library need MirrorDash 0.5 or newer; `mirrordash-sdk dev-setup` installs
the right version.

---

## Words used in this guide

| Word | Meaning |
| :--- | :--- |
| **API** | A web address that answers with data (often JSON) instead of a web page. |
| **API key** | A password a service gives you, so it knows who is asking. |
| **async / await** | `async def` makes a function that can wait without blocking other modules; `await` is where it waits. |
| **broadcast** | Sending your module's HTML to the screen. |
| **component library** | `http://localhost:8000/design`: the mirror's building blocks for the look, with code to copy. |
| **entry point** | A line in `pyproject.toml` that tells the mirror which class is your module. `create-module` writes it. |
| **event bus** | The mirror's way of passing messages between modules (and from hardware). |
| **header** | Extra information sent with a web request, for example an API key. |
| **Jinja** | The `{{ ... }}` and `{% ... %}` in templates: they fill in values and repeat or hide parts. |
| **JSON** | A text format for data: `{"temperature": 21}`. Python reads it as a dictionary. |
| **release** | A version of your module on GitHub that mirrors can install. |
| **shadow DOM** | Your module's own little box on the page. Styles from outside don't get in, yours don't get out. |
| **template** | The HTML file (`widget.html`) that shows your data. |
