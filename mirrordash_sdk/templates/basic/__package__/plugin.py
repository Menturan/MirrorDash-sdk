import asyncio
import logging
from datetime import datetime

logger = logging.getLogger("mirrordash.modules.$package_name")


class $class_name:
    # Keeps pytest from collecting this class as a test
    __test__ = False

    def __init__(self, config):
        # config holds this module's settings from the admin page (see config_schema.json), plus:
        # "data_dir" (kept and backed up), "cache_dir" (may be cleared) and "globals" (language, units, …).
        # The mirror adds self.render_template, self.translate and self.fetch_json after __init__.
        self.config = config
        self.name = "$package_name"
        self.interval = config.get("interval", 30)

    async def run_loop(self, broadcast_func):
        """Runs as long as the mirror does: work out what to show, send it, wait, repeat."""
        while True:
            try:
                html = self.render_template("widget.html", current_time=datetime.now().strftime("%H:%M"))
                await broadcast_func(self.name, html)
            except asyncio.CancelledError:
                raise  # the mirror is stopping this module: let it
            except Exception as e:
                logger.error(f"{self.name}: {e}", exc_info=True)
            await asyncio.sleep(self.interval)
