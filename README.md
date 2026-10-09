# MirrorDash SDK

Build modules for [MirrorDash](https://github.com/Menturan/MirrorDash): small panels on the mirror, such as weather, a calendar or your own data.

## Quick start

You need [uv](https://docs.astral.sh/uv/getting-started/installation/). Then one command creates a module, sets up a local mirror with it, starts it and opens it in your browser:

```bash
uvx mirrordash-sdk quickstart mirrordash-my-widget
```

The module shows example data right away. Change it in `mirrordash-my-widget/mirrordash_my_widget/`: save a file and the mirror shows the change by itself. Stop it with `Ctrl+C`, start it again with `uvx mirrordash-sdk start` in the module's folder. The admin page of this local mirror is at `http://localhost:8000/admin`, password `mirrordash`.

**New to this?** The [module guide](https://github.com/Menturan/MirrorDash-sdk/blob/master/MODULE_GUIDE.md) walks you through building a real module step by step, in about half an hour.

## Templates

| Template | For a module that… | |
| :--- | :--- | :--- |
| `api` (default for `quickstart`) | fetches data from a web API with an API key and shows a value and a few rows | `--template api` |
| `basic` | works out what to show by itself, without the internet | `--template basic` |

Both show their data with components from the mirror's component library (`http://localhost:8000/design`), so they need no CSS, and both come with tests (`uv run pytest`).

## Commands

```bash
uvx mirrordash-sdk quickstart <name> [-t api|basic]   # everything below in one go
uvx mirrordash-sdk create-module <name> [-t basic|api] # just create the module
uvx mirrordash-sdk dev-setup -e                        # a local mirror (.venv) with this module on it
uvx mirrordash-sdk start                               # start the local mirror: http://localhost:8000/
uvx mirrordash-sdk validate .                          # check the module before you push it
uvx mirrordash-sdk release 1.0.0                       # a new version mirrors can install
```

## Share your module

Push it to GitHub once, then run `uvx mirrordash-sdk release 1.0.0` for every version. It sets the version in `pyproject.toml`, tags it `v1.0.0`, pushes, and makes the **GitHub Release** (with the [`gh`](https://cli.github.com/) tool, or it gives you the link). Mirrors install the module from its Git URL under **Admin → Modules**, and offer updates when you make a new release. Nothing needs to be built or uploaded anywhere else. Details: [MODULE_GUIDE.md, part 11](https://github.com/Menturan/MirrorDash-sdk/blob/master/MODULE_GUIDE.md#11-sharing-your-module).

## Learn more

- **[MODULE_GUIDE.md](https://github.com/Menturan/MirrorDash-sdk/blob/master/MODULE_GUIDE.md)**: a step-by-step tutorial, then everything else: the component library, `fetch_json`/`fetch`, settings, translations, testing, sharing, troubleshooting.
- **[MODULE_AGENTS.md](https://github.com/Menturan/MirrorDash-sdk/blob/master/MODULE_AGENTS.md)**: the same rules, short, for AI coding agents.
- `http://localhost:8000/design` while your local mirror runs: the component library, every building block with code to copy.

## Developing the SDK itself

```bash
uv sync && uv run pytest   # the tests also generate every template and run its tests
```

Releases: `python3 scripts/release.py` (try `--dry-run` first). It checks master and the tests, sets the version, pushes and tags `vX.Y.Z`; GitHub Actions then tests, builds and publishes it to PyPI.
