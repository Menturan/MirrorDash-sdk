# $folder_name

$description

## Get an API key

1. Create an account at the service's website (link here).
2. Copy your API key.
3. On the mirror: **Modules → $title → API Key**, paste it and save.

The key is only sent to the service, in a request header; the mirror never logs it.

## Send it a value (optional)

Set a **Token** in the module's settings. Then a phone shortcut, a sensor or Home Assistant can send the module a
value, shown as *Sent* and kept across restarts:

```bash
curl -X POST http://mirrordash.local/api/modules/$package_name/value \
     -H "X-Token: <your token>" -H "Content-Type: application/json" -d '{"value": 12}'
```

## Make it yours

This module shows every part a module can have, each marked `── <part> ──` in `$package_name/plugin.py`,
`templates/widget.html` and `tests/test_plugin.py`. Keep what you need and delete the rest, with its settings in
`config_schema.json` and its texts in `translations/`:

| Part | What it does | Settings | Texts |
| :--- | :--- | :--- | :--- |
| Fetching data | Fetches JSON from an API with a key; example data until there is one; says what went wrong | `api_key`, `location`, `interval` | `missing_key`, `key_rejected`, `offline`, `fetch_failed`, `last_updated` |
| Settings | A dropdown (`enum`) between two looks from the component library | `layout` | |
| Global settings | Shows times as the mirror does (24h or 12h) | | |
| A device at home | Shows what a device on the home network answers (`self.fetch`, not JSON) | `device_url` (`"format": "lan-url"`) | `device` |
| Saving files | Keeps a value in `data_dir` across restarts | | |
| Your own web address | `POST …/value`, only with the token | `token` | `sent` |
| Messages | Hears the mirror's button; publishes its value for other modules (`public=True`) | | |
| GPIO pins of your own | Switches a relay on a double press of the button | `relay_pin` | `relay`, `on`, `off` |
| Home Assistant (MQTT) | Shows the value and the relay in Home Assistant, which may switch the relay or ask for an update, once the owner shares the module (MirrorDash 0.10) | `exposes` | |
| Fetching in the dark | `keep_running`: fetch while the screen is off too | | |
| Your own CSS and script | The "… min ago" line, calm while a video plays | | `minutes_ago` |

To change what is fetched: `URL` at the top of `plugin.py` (the **Location** setting is sent as `?q=…`), the
`Authorization: Bearer` header in `render()` (some APIs want another, like `X-Api-Key`), and `parse()`, which picks
one big `value` and a few `rows` from the answer. The [module guide](https://github.com/Menturan/mirrordash-sdk/blob/master/MODULE_GUIDE.md) explains every part.

## Develop

```bash
uv run pytest                    # the module's tests
uvx mirrordash-sdk validate .    # checks the module before you push it
```

Try it on a local mirror: see the [MirrorDash SDK](https://github.com/Menturan/mirrordash-sdk#quick-start).

Share it: push it to GitHub, then `uvx mirrordash-sdk release 0.1.0` makes the release mirrors install.

## Screenshot

Put a picture of the module named `screenshot.png` next to this file; GitHub shows it on your module's page. (The mirror's module list shows your repository's GitHub description, its "About" text.)

![Screenshot](screenshot.png)
