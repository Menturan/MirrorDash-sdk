# MirrorDash SDK

Build modules for [MirrorDash](https://github.com/Menturan/MirrorDash): small panels on the mirror, such as weather, a calendar or your own data.

## Quick start

You need [uv](https://docs.astral.sh/uv/getting-started/installation/). Then one command creates a module, sets up a local mirror with it, starts it and opens it in your browser:

```bash
uvx mirrordash-sdk quickstart mirrordash-my-widget
```

The module shows example data right away. Change it in `mirrordash-my-widget/mirrordash_my_widget/`; restart with `uvx mirrordash-sdk start` (inside the module directory) to see your changes. The admin page of this local mirror is at `http://localhost:8000/admin`, password `mirrordash`.

## Templates

| Template | For a module that… | |
| :--- | :--- | :--- |
| `api` (default for `quickstart`) | fetches data from a web API with an API key and shows a value and a few rows | `--template api` |
| `basic` | works out what to show by itself, without the internet | `--template basic` |

Both show their data with the mirror's own building blocks (big numbers, label–value rows, messages), so they need no CSS, and both come with tests (`uv run pytest`).

## Commands

```bash
uvx mirrordash-sdk quickstart <name> [-t api|basic]   # everything below in one go
uvx mirrordash-sdk create-module <name> [-t basic|api] # just create the module
uvx mirrordash-sdk dev-setup -e                        # a local mirror (.venv) with this module on it
uvx mirrordash-sdk start                               # start the local mirror: http://localhost:8000/
uvx mirrordash-sdk validate .                          # check the module before you publish it
uvx mirrordash-sdk build                               # build the package
uvx mirrordash-sdk publish                             # validate and upload to PyPI
```

## Learn more

- **[MODULE_GUIDE.md](MODULE_GUIDE.md)**: the reference: the plugin class, `fetch_json`, settings, translations, the building blocks, publishing.
- **[MODULE_AGENTS.md](MODULE_AGENTS.md)**: the same rules, short, for AI coding agents.
- `http://localhost:8000/design` while your local mirror runs: every building block with markup to copy.

## Developing the SDK itself

```bash
uv sync && uv run pytest   # the tests also generate every template and run its tests
```

Releases: `python3 scripts/release.py` (try `--dry-run` first). It checks master and the tests, sets the version, pushes and tags `vX.Y.Z`; GitHub Actions then tests, builds and publishes it to PyPI.
