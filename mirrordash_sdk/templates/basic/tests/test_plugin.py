import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from $package_name.plugin import $class_name


def test_reads_its_settings():
    assert $class_name({"interval": 15}).interval == 15


@pytest.mark.asyncio
async def test_run_loop_sends_the_rendered_html():
    module = $class_name({})
    module.render_template = MagicMock(return_value="<div>rendered</div>")  # the mirror adds this
    broadcast = AsyncMock()

    # Stop the endless loop at its first sleep
    with patch("asyncio.sleep", side_effect=asyncio.CancelledError), pytest.raises(asyncio.CancelledError):
        await module.run_loop(broadcast)

    broadcast.assert_called_once_with("$package_name", "<div>rendered</div>")
