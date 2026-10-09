import asyncio
import logging
from datetime import datetime

logger = logging.getLogger("mirrordash.modules.$package_name")

# --- Change these for your API ------------------------------------------------------------
URL = "https://api.example.com/v1/current"  # the address to fetch; the settings are added as ?q=…


def parse(data: dict) -> dict:
    """Turn the API's JSON answer into what templates/widget.html shows: a big value and some rows."""
    return {
        "value": data.get("value", "–"),
        "rows": [("Min", data.get("min", "–")), ("Max", data.get("max", "–"))],
    }


# Shown, marked as example data, until an API key is set: an answer like the API's, so you see the design at once
EXAMPLE = {"value": 21, "min": 18, "max": 24}
# -------------------------------------------------------------------------------------------

# What to say when fetching fails: fetch_json's error -> (translation key, English text)
ERRORS = {
    "rejected": ("key_rejected", "The API key was rejected. Check it in the module's settings."),
    "offline": ("offline", "Can't reach the service."),
}


class $class_name:
    # Keeps pytest from collecting this class as a test
    __test__ = False

    def __init__(self, config):
        # config holds this module's settings from the admin page (see config_schema.json).
        # The mirror adds self.render_template, self.translate and self.fetch_json after __init__.
        self.config = config
        self.name = "$package_name"
        self.interval = config.get("interval", 600)
        self.api_key = config.get("api_key", "")
        self.location = config.get("location", "")
        self.updated = None  # time of the last successful update

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
        if not self.api_key:
            return self.render_template("widget.html", data=parse(EXAMPLE), icon="key-round",
                                        message=self.translate("missing_key", "Example data. Add an API key in the module's settings."))

        # The key goes in a header, so it never ends up in a log or in a cached URL.
        # On a failure, data is the last good answer (also after a restart) and error says what went wrong.
        # max_age: an answer younger than the interval is reused, so saving a setting or a restart makes no call.
        data, error = await self.fetch_json(URL, headers={"Authorization": f"Bearer {self.api_key}"},
                                            params={"q": self.location}, max_age=self.interval)
        if not error:
            self.updated = datetime.now().strftime("%H:%M")
            return self.render_template("widget.html", data=parse(data), message=None)

        key, text = ERRORS.get(error, ("fetch_failed", "Couldn't update."))
        message = self.translate(key, text)
        if data is not None and self.updated:
            message += " " + self.translate("last_updated", "Last updated {time}.").format(time=self.updated)
        return self.render_template("widget.html", data=parse(data) if data is not None else None,
                                    message=message, icon="key-round" if error == "rejected" else "cloud-off")
