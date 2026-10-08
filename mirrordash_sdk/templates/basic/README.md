# $folder_name

$description

## Develop

```bash
uv run pytest                    # the module's tests
uvx mirrordash-sdk validate .    # checks the module before you push it
```

Try it on a local mirror: see the [MirrorDash SDK](https://github.com/Menturan/mirrordash-sdk#quick-start).

Share it: push to GitHub and make a GitHub Release (tag `v` + the version in `pyproject.toml`); mirrors install it from the Git URL.

## Settings

Describe each setting in the module's settings here, and any account or key it needs.

## Screenshot

Put a picture of the module named `screenshot.png` next to this file; the mirror's module list shows it.

![Screenshot](screenshot.png)
