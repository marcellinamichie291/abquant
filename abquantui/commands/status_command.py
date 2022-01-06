from threading import Thread
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from abquantui.abquant_application import AbquantApplication


class StatusCommand:

    def status(self: "AbquantApplication"):
        res = self.strategy_lifecycle.status()
        self._notify(res)

