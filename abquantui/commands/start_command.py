from threading import Thread
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from abquantui.abquant_application import AbquantApplication


class StartCommand:

    def start(self: "AbquantApplication"):
        Thread(target=self.start_in_thread, name='startCommandThread').start()

    def start_in_thread(self):
        self._notify('Starting the strategy')
        self.strategy_lifecycle.start()
        self._notify('Starting work is done')
