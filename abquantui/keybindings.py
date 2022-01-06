from prompt_toolkit.key_binding import KeyBindings
from threading import Thread
from abquantui.commands.shutdown_command import kill_program


def load_key_bindings(hb) -> KeyBindings:
    bindings = KeyBindings()

    @bindings.add("c-c", "c-c")
    def exit_(event):
        hb.app.log("\n[Double CTRL + C] keyboard exit")
        Thread(target=kill_program, args=(3,)).start()
        hb.app.exit()
    return bindings