# $folder_name

$description

## Get an API key

1. Create an account at the service's website (link here).
2. Copy your API key.
3. On the mirror: **Modules → $title → API Key**, paste it and save.

The key is only sent to the service, in a request header; the mirror never logs it.

## Make it yours

Everything to change is at the top of `$package_name/plugin.py`:

- `URL`: the address of the API. The **Location** setting is sent as `?q=…`; change `params` in `render()` if your API wants other names.
- The `Authorization: Bearer` header in `render()`: some APIs want the key in another header (for example `X-Api-Key`).
- `parse()`: picks what to show from the API's answer: one big `value` and a few `rows`.

`templates/widget.html` shows it with the mirror's own classes; see the classes at `http://localhost:8000/design` while the dev server runs.

## Develop

```bash
uv run pytest                    # the module's tests
uvx mirrordash-sdk validate .    # checks the module before you push it
```

Try it on a local mirror: see the [MirrorDash SDK](https://github.com/Menturan/mirrordash-sdk#quick-start).

Share it: push to GitHub and make a GitHub Release (tag `v` + the version in `pyproject.toml`); mirrors install it from the Git URL.

## Screenshot

Put a picture of the module named `screenshot.png` next to this file; the mirror's module list shows it.

![Screenshot](screenshot.png)
