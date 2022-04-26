import asyncio
import time
from threading import Thread
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from abquantui.abquant_application import AbquantApplication


class StatusCommand:

    def status(self: "AbquantApplication", live):
        if live:
            asyncio.create_task(self.status_live())
        else:
            res = self.strategy_lifecycle.status()
            self._notify(res)

    async def status_live(self: "AbquantApplication"):
        self.app.live_updates = True
        while self.app.live_updates:
            content = self.strategy_lifecycle.status_live()
            if type(content) != str:
                content = 'status_live() should return type str'

            content += '\n\n Press escape key to stop update'
            await self.cls_display_delay(content, 1)
        self.app.live_updates = False


    def status_in_thread(self: "AbquantApplication"):
        self.app.live_updates = True
        ever = time.time()
        while self.app.live_updates and time.time() - ever < 10:
            self.cls_display_delay(str(time.time()))
            print('test')
        self.app.live_updates = False