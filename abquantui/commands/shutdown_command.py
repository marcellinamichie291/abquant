import asyncio
import os, time
import signal
from typing import TYPE_CHECKING
from threading import Thread

if TYPE_CHECKING:
    from abquantui.abquant_application import AbquantApplication


def kill_program(delay=0):
    time.sleep(delay)
    os.kill(os.getpid(), signal.SIGKILL)


class ShutdownCommand:

    def shutdown(self: "AbquantApplication"):
        asyncio.create_task(self.confirm_shutdown())

    async def confirm_shutdown(self: "AbquantApplication"):
        self.app.clear_input()
        self.placeholder_mode = True
        self.app.hide_input = True
        to_shutdown = True
        prompt = 'Would you like to kill -9 the program (Yes/No)? >>> '
        answer = await self.app.prompt(prompt=prompt)
        if answer.lower() not in ("yes", "y"):
            to_shutdown = False

        if to_shutdown:
            Thread(target=kill_program, args=(3,)).start()
            self.app.exit()
        self.placeholder_mode = False
        self.app.hide_input = False
        self.app.change_prompt(prompt=">>> ")
