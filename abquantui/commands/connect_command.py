from threading import Thread
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from abquantui.abquant_application import AbquantApplication


class ConnectCommand:

    def connect(self: "AbquantApplication"):
        Thread(target=self.connect_in_thread, name='ConnectThread').start()

    def connect_in_thread(self):
        self._notify('Starting connect gateway and add and init strategy')
        self._notify('\n Please do nothing and wait until this work is done!')
        res = self.strategy_lifecycle.connect_gateway()
        self._notify(res)
        self._notify('Done， then you can start your strategy')
