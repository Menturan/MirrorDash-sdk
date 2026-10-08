from unittest.mock import AsyncMock, MagicMock

import pytest

from $package_name.plugin import $class_name


def make_module(**settings):
    """The module as the mirror sets it up, with the mirror's helpers replaced by fakes."""
    module = $class_name({"api_key": "my-key", "location": "Oslo", **settings})
    module.render_template = MagicMock(side_effect=lambda name, **context: context)  # returns what the template gets
    module.translate = lambda key, default=None: default
    module.fetch_json = AsyncMock()
    return module


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
    module.fetch_json.return_value = ({"value": 21, "min": 18, "max": 24}, None)
    shown = await module.render()
    assert shown["data"]["value"] == 21
    assert shown["message"] is None
    assert module.fetch_json.call_args.kwargs["headers"] == {"Authorization": "Bearer my-key"}
    assert module.fetch_json.call_args.kwargs["params"] == {"q": "Oslo"}


@pytest.mark.asyncio
async def test_a_failed_update_keeps_the_last_answer_and_says_so():
    module = make_module()
    module.fetch_json.return_value = ({"value": 21}, None)
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
