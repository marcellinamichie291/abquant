from threading import Thread
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from abquantui.abquant_application import AbquantApplication


class StopCommand:

    def stop(self: "AbquantApplication"):
        self.strategy_lifecycle.stop()
        self._notify('stop command executed')

