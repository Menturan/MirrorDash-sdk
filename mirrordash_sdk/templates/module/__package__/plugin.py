import asyncio
import hmac
import json
import logging
import os
from datetime import datetime

from fastapi import APIRouter, Header, HTTPException  # on the mirror already: not in pyproject's dependencies

logger = logging.getLogger("mirrordash.modules.$package_name")

# Every part of this module is marked "── <part> ──". Delete the parts you don't need: the README says which
# settings (config_schema.json), texts (translations/) and tests (tests/test_plugin.py) go with each.

# ── Fetching data ── change these for your API ─────────────────────────────────────────────────────────
URL = "https://api.example.com/v1/current"  # the address to fetch; the Location setting is added as ?q=…


def parse(data: dict) -> dict:
    """Turn the API's JSON answer into what templates/widget.html shows: a big value and some rows."""
    return {
        "value": data.get("value", "–"),
        "rows": [("Min", data.get("min", "–")), ("Max", data.get("max", "–"))],
    }


# Shown, marked as example data, until an API key is set: an answer like the API's, so you see the design at once
EXAMPLE = {"value": 21, "min": 18, "max": 24}

# What to say when fetching fails: fetch_json's error -> (translation key, English text)
ERRORS = {
    "rejected": ("key_rejected", "The API key was rejected. Check it in the module's settings."),
    "offline": ("offline", "Can't reach the service."),
}
# ────────────────────────────────────────────────────────────────────────────────────────────────────────


class $class_name:
    # ── Fetching in the dark ── True: fetch_json keeps calling while the screen is off (a data logger).
    # False (the usual): a fetch waits until someone is in front of the mirror again.
    keep_running = False

    def __init__(self, config):
        # config: this module's settings from the admin page (config_schema.json), plus what the mirror adds.
        # The mirror's helpers (self.render_template, self.translate, self.fetch_json, self.fetch, self.gpio, self.expose)
        # are added after __init__: use them from run_loop.
        self.config = config
        self.name = "$package_name"
        self.interval = config.get("interval", 600)
        self.layout = config.get("layout", "list")  # ── Settings ── a dropdown: rows or a grid
        self.changed = asyncio.Event()  # set: render() again at once, not at the next interval

        # ── Fetching data ──
        self.api_key = config.get("api_key", "")
        self.location = config.get("location", "")
        self.updated = None  # when the last fetch worked
        self.update_now = False  # Home Assistant's Update now: the next fetch calls even if the answer is young

        # ── Global settings ── the same for every module: language, time zone, units, location
        self.time_format = config.get("globals", {}).get("time_format", "24h")

        # ── A device at home ── the module reaches the home network only at "format": "lan-url" addresses
        self.device_url = config.get("device_url", "")

        # ── Saving files ── data_dir is kept and backed up, cache_dir may be cleared; each copy has its own
        self.state_file = os.path.join(config["data_dir"], "state.json") if config.get("data_dir") else None
        self.state = self.load_state()

        # ── Your own web address ── POST http://mirrordash.local<api_path>/value, with the Token setting
        self.token = config.get("token", "")
        self.api_path = config.get("api_path", "")
        self.router = APIRouter()
        self.router.post("/value")(self.on_value)

        # ── Messages ── from the mirror's hardware, and other modules' public ones
        self.event_bus = config.get("event_bus")  # not there in a test
        if self.event_bus:
            self.event_bus.subscribe("hardware.button", self.on_button)
            # Another module's public messages, the same way: self.event_bus.subscribe("mirrordash_x.y", ...)

        # ── GPIO pins of your own ── a relay the mirror's button switches
        self.relay_pin = config.get("relay_pin", 0)
        self.relay = None
        self.relay_on = False
        self.gpio_error = None

    async def render(self) -> str:
        """The mirror shows what this returns, every interval and at once after self.changed.set(). No loop of
        your own: write run_loop(self, broadcast_func) only for your own timing (a ticking clock, a stream)."""
        if self.relay_pin and not self.relay and not self.gpio_error:  # ── GPIO pins of your own ── once
            await self.take_relay()
        data, message, icon, since = None, None, "cloud-off", None

        # ── Fetching data ──
        if not self.api_key:
            data, icon = parse(EXAMPLE), "key-round"
            message = self.translate("missing_key", "Example data. Add an API key in the module's settings.")
        else:
            # The key goes in a header, so it never ends up in a log or in a cached URL. On a failure, answer is
            # the last good one (also after a restart) and error says what went wrong. An answer younger than
            # the interval is reused, so saving a setting or a restart makes no call; max_age=0 always calls.
            answer, error = await self.fetch_json(URL, headers={"Authorization": f"Bearer {self.api_key}"},
                                                  params={"q": self.location}, max_age=0 if self.update_now else None)
            self.update_now = False
            data = parse(answer) if answer is not None else None
            if not error:
                self.updated = datetime.now()
                # ── Messages ── a public one: every module can subscribe to "$package_name.value"
                if self.event_bus:
                    self.event_bus.publish(f"{self.name}.value", data["value"], public=True)
                # ── Home Assistant (MQTT) ── the value as a sensor there
                await self.share("value", data["value"])
            else:
                key, text = ERRORS.get(error, ("fetch_failed", "Couldn't update."))
                message = self.translate(key, text)
                icon = "key-round" if error == "rejected" else "cloud-off"
                if data and self.updated:
                    message += " " + self.translate("last_updated", "Last updated {time}.").format(
                        time=self.clock(self.updated))
            if data and self.updated:
                since = int(self.updated.timestamp() * 1000)  # the data's time, for the card's script

        rows = []
        # ── Your own web address ── the last value sent to it, kept in data_dir
        if "sent" in self.state:
            rows.append((self.translate("sent", "Sent"), self.state["sent"]))
        # ── A device at home ── self.fetch for an answer that isn't JSON: data is bytes
        if self.device_url:
            reply, _ = await self.fetch(self.device_url)
            rows.append((self.translate("device", "At home"), reply.decode(errors="replace").strip()[:40] if reply else "–"))
        # ── GPIO pins of your own ──
        if self.relay:
            rows.append((self.translate("relay", "Relay"),
                         self.translate("on", "On") if self.relay_on else self.translate("off", "Off")))
        if self.gpio_error and not message:
            message, icon = self.gpio_error, "circuit-board"

        if rows:
            data = {"value": data["value"] if data else "–", "rows": [*(data["rows"] if data else []), *rows]}
        return self.render_template("widget.html", data=data, layout=self.layout, message=message, icon=icon,
                                    since=since)

    def clock(self, moment: datetime) -> str:
        """── Global settings ── a time as the mirror shows times."""
        return moment.strftime("%I:%M %p" if self.time_format == "12h" else "%H:%M")

    # ── Saving files ──
    def load_state(self) -> dict:
        if not self.state_file:
            return {}
        try:
            with open(self.state_file, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}  # not saved yet, or a broken file: start over

    def save_state(self) -> None:
        if self.state_file:
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f)

    # ── Your own web address ──
    async def on_value(self, body: dict, x_token: str = Header(default="")):
        """POST <api_path>/value with {"value": 12} and the header X-Token: <the Token setting>. Anyone on the home
        network can call it, so without the right token it does nothing (and with no token set, never)."""
        if not self.token or not hmac.compare_digest(x_token.encode(), self.token.encode()):
            raise HTTPException(status_code=403)
        self.state["sent"] = str(body.get("value", ""))[:40]
        self.save_state()
        self.changed.set()
        return {"ok": True}

    # ── Messages ──
    async def on_button(self, data: dict):
        """A press on the mirror's button (what the owner set it to do has happened already): a double press
        switches the relay."""
        if self.relay and data.get("press") == "double":
            await self.switch_relay(not self.relay_on)

    # ── Home Assistant (MQTT) ── what config_schema.json's "exposes" declares, once the owner shares this module
    # (Admin → Settings → MQTT): Home Assistant shows the value and the relay, and may switch it or ask for an update
    async def share(self, name: str, value):
        """A value of something "exposes" declares. A mirror before MirrorDash 0.10 has no self.expose: nothing then."""
        if hasattr(self, "expose"):
            await self.expose(name, value)

    async def on_control(self, name: str, value):
        """A command from Home Assistant, only for what "exposes" marks "control" and the owner allowed, its value
        already checked against the declaration: True/False for the relay (a switch), None for a button."""
        if name == "relay" and self.relay:  # with GPIO pins of your own
            await self.switch_relay(value)
        elif name == "update":
            self.update_now = True
            self.changed.set()

    # ── GPIO pins of your own ──
    async def take_relay(self):
        """The relay's pin, if one is set. A pin the mirror uses, or a computer without GPIO, says why instead."""
        if self.relay_pin:
            try:
                self.relay = await self.gpio([self.relay_pin], output=True)
                await self.share("relay", self.relay_on)  # ── Home Assistant (MQTT) ──
            except RuntimeError as e:
                self.gpio_error = str(e)

    async def switch_relay(self, on: bool):
        """The relay on or off: from the mirror's button, or from Home Assistant."""
        self.relay_on = on
        self.relay.set(self.relay_pin, int(on))
        await self.share("relay", on)  # ── Home Assistant (MQTT) ──
        self.changed.set()
