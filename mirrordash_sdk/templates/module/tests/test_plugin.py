from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from $package_name.plugin import $class_name

# Each test is marked with the part of plugin.py it checks: delete it with that part.


def make_module(tmp_path=None, **settings):
    """The module as the mirror sets it up, with the mirror's helpers replaced by fakes."""
    config = {"api_key": "my-key", "location": "Oslo", **settings}
    if tmp_path:
        config["data_dir"] = str(tmp_path)
    module = $class_name(config)
    module.render_template = MagicMock(side_effect=lambda name, **context: context)  # returns what the template gets
    module.translate = lambda key, default=None: default
    module.fetch_json = AsyncMock(return_value=({"value": 21, "min": 18, "max": 24}, None))
    module.fetch = AsyncMock(return_value=(b"door closed\n", None))
    module.gpio = AsyncMock(return_value=MagicMock())  # the lines it hands out: .set(pin, value), .get(pin)
    module.expose = AsyncMock()  # Home Assistant (MQTT)
    return module


# ── Fetching data ──

@pytest.mark.asyncio
async def test_without_a_key_it_shows_example_data_and_asks_for_one():
    module = make_module(api_key="")
    shown = await module.render()
    assert shown["data"]["value"] == 21
    assert "Example data" in shown["message"] and "API key" in shown["message"]
    module.fetch_json.assert_not_called()


@pytest.mark.asyncio
async def test_shows_the_answer_and_sends_the_key_in_a_header():
    module = make_module()
    shown = await module.render()
    assert shown["data"] == {"value": 21, "rows": [("Min", 18), ("Max", 24)]}
    assert shown["message"] is None and shown["since"]
    assert module.fetch_json.call_args.kwargs["headers"] == {"Authorization": "Bearer my-key"}
    assert module.fetch_json.call_args.kwargs["params"] == {"q": "Oslo"}


@pytest.mark.asyncio
async def test_a_failed_update_keeps_the_last_answer_and_says_so():
    module = make_module()
    await module.render()
    module.fetch_json.return_value = ({"value": 21}, "offline")  # fetch_json hands back the last answer
    shown = await module.render()
    assert shown["data"]["value"] == 21
    assert "Last updated" in shown["message"]


@pytest.mark.asyncio
async def test_a_rejected_key_says_so():
    module = make_module()
    module.fetch_json.return_value = (None, "rejected")
    shown = await module.render()
    assert shown["data"] is None
    assert "rejected" in shown["message"]


# ── Global settings ──

def test_times_follow_the_mirrors_time_format():
    module = make_module(globals={"time_format": "12h"})
    assert module.clock(datetime(2026, 1, 1, 15, 5)) == "03:05 PM"


# ── A device at home ──

@pytest.mark.asyncio
async def test_shows_what_the_device_at_home_answers():
    module = make_module(device_url="http://192.168.1.20/status")
    shown = await module.render()
    assert ("At home", "door closed") in shown["data"]["rows"]
    module.fetch.assert_called_once_with("http://192.168.1.20/status", max_age=600)


# ── Your own web address ── and ── Saving files ──

@pytest.mark.asyncio
async def test_a_sent_value_needs_the_token_and_is_kept_across_a_restart(tmp_path):
    module = make_module(tmp_path, token="s3cret")
    for token in ("", "wrong"):
        with pytest.raises(HTTPException):
            await module.on_value({"value": 12}, x_token=token)
    assert await module.on_value({"value": 12}, x_token="s3cret") == {"ok": True}

    restarted = make_module(tmp_path, token="s3cret")  # a new copy reads data_dir again
    assert ("Sent", "12") in (await restarted.render())["data"]["rows"]


@pytest.mark.asyncio
async def test_with_no_token_set_nobody_can_send():
    with pytest.raises(HTTPException):
        await make_module().on_value({"value": 12}, x_token="")


# ── Messages ──

@pytest.mark.asyncio
async def test_subscribes_to_the_button_and_publishes_its_value():
    bus = MagicMock()
    module = make_module(event_bus=bus)
    bus.subscribe.assert_called_once_with("hardware.button", module.on_button)
    await module.render()
    bus.publish.assert_called_once_with(f"{module.name}.value", 21, public=True)


# ── GPIO pins of your own ──

@pytest.mark.asyncio
async def test_a_double_press_switches_the_relay():
    module = make_module(relay_pin=27)
    await module.take_relay()
    module.gpio.assert_called_once_with([27], output=True)
    await module.on_button({"press": "single"})
    await module.on_button({"press": "double"})
    module.relay.set.assert_called_once_with(27, 1)
    assert ("Relay", "On") in (await module.render())["data"]["rows"]


@pytest.mark.asyncio
async def test_a_pin_it_cant_have_says_why():
    module = make_module(relay_pin=2)
    module.gpio.side_effect = RuntimeError("No GPIO 2: the I²C sensor uses it")
    await module.take_relay()
    assert (await module.render())["message"] == "No GPIO 2: the I²C sensor uses it"


# ── Home Assistant (MQTT) ──

@pytest.mark.asyncio
async def test_home_assistant_sees_the_value_and_the_relay():
    module = make_module(relay_pin=27)
    await module.take_relay()
    await module.render()
    module.expose.assert_any_await("relay", False)
    module.expose.assert_any_await("value", 21)


@pytest.mark.asyncio
async def test_home_assistant_switches_the_relay_and_asks_for_an_update():
    module = make_module(relay_pin=27)
    await module.take_relay()
    await module.on_control("relay", True)  # what the mirror sends: checked against config_schema.json's "exposes"
    module.relay.set.assert_called_once_with(27, 1)
    module.expose.assert_awaited_with("relay", True)
    module.changed.clear()
    await module.on_control("update", None)
    assert module.changed.is_set()


@pytest.mark.asyncio
async def test_a_mirror_before_mqtt_has_no_expose_and_nothing_breaks():
    module = make_module(relay_pin=27)
    del module.expose
    await module.take_relay()
    await module.render()
