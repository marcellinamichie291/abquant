
import asyncio
import logging
import threading
from prompt_toolkit.application import Application
from prompt_toolkit.clipboard.pyperclip import PyperclipClipboard
from prompt_toolkit.completion import Completer
from prompt_toolkit.document import Document
from prompt_toolkit.layout.processors import BeforeInput, PasswordProcessor
from prompt_toolkit.key_binding import KeyBindings
from typing import Callable, Optional, Dict, Any, TYPE_CHECKING
from hummingbot.client.ui.interface_utils_ab import start_timer, start_process_monitor
from hummingbot.client.ui.style import load_style
from hummingbot.client.ui.layout import (
    create_input_field,
    create_log_field,
    create_log_toggle,
    create_output_field,
    create_output_field_ab,
    create_search_field,
    generate_layout,
    create_timer,
    create_process_monitor,
    create_live_field,
    create_tab_button,
    generate_layout_2,
)


class AbquantCLI:
    def __init__(self,
                 input_handler: Callable,
                 bindings: KeyBindings,
                 completer: Completer,
                 **kwargs):
        self.input_field = create_input_field(completer=completer)
        self.output_field = create_output_field()
        self.search_field = create_search_field()
        self.log_field = create_log_field(self.search_field)
        self.right_pane_toggle = create_log_toggle(self.toggle_right_pane)
        self.log_field_button = create_tab_button("Log-pane", self.log_button_clicked)
        self.timer = create_timer()
        self.process_usage = create_process_monitor()
        self.layout, self.layout_components = generate_layout_2(self.input_field, self.output_field, self.log_field,
                                                                self.search_field,
                                                                self.right_pane_toggle, self.log_field_button,
                                                                self.timer,
                                                                self.process_usage,
                                                                **kwargs
                                                                )
        # add self.to_stop_config to know if cancel is triggered
        self.to_stop_config: bool = False

        self.live_updates = False
        self.bindings = bindings
        self.input_handler = input_handler
        self.input_field.accept_handler = self.accept
        self.app: Optional[Application] = None

        # settings
        self.prompt_text = ">>> "
        self.pending_input = None
        self.input_event = None
        self.hide_input = False

        # start ui tasks
        loop = asyncio.get_event_loop()
        loop.create_task(start_timer(self.timer))
        loop.create_task(start_process_monitor(self.process_usage))

    async def run(self):
        self.app = Application(layout=self.layout, full_screen=True, key_bindings=self.bindings, style=load_style(),
                               mouse_support=True, clipboard=PyperclipClipboard())
        await self.app.run_async()

    def accept(self, buff):
        self.pending_input = self.input_field.text.strip()

        if self.input_event:
            self.input_event.set()

        try:
            if self.hide_input:
                output = ''
            else:
                output = '\n>>>  {}'.format(self.input_field.text,)
                self.input_field.buffer.append_to_history()
        except BaseException as e:
            output = str(e)

        self.log(output)
        self.input_handler(self.input_field.text)

    def clear_input(self):
        self.pending_input = None

    def log(self, text: str, save_log: bool = True):
        if save_log:
            if self.live_updates:
                self.output_field.log(text, silent=True)
            else:
                self.output_field.log(text)
        else:
            self.output_field.log(text, save_log=False)

    def change_prompt(self, prompt: str, is_password: bool = False):
        self.prompt_text = prompt
        processors = []
        if is_password:
            processors.append(PasswordProcessor())
        processors.append(BeforeInput(prompt))
        self.input_field.control.input_processors = processors

    async def prompt(self, prompt: str, is_password: bool = False) -> str:
        self.change_prompt(prompt, is_password)
        self.app.invalidate()
        self.input_event = asyncio.Event()
        await self.input_event.wait()

        temp = self.pending_input
        self.clear_input()
        self.input_event = None

        if is_password:
            masked_string = "*" * len(temp)
            self.log(f"{prompt}{masked_string}")
        else:
            self.log(f"{prompt}{temp}")
        return temp

    def set_text(self, new_text: str):
        self.input_field.document = Document(text=new_text, cursor_position=len(new_text))

    def toggle_hide_input(self):
        self.hide_input = not self.hide_input

    def toggle_right_pane(self):
        if self.layout_components["pane_right"].filter():
            self.layout_components["pane_right"].filter = lambda: False
            self.layout_components["item_top_toggle"].text = '< log pane'
        else:
            self.layout_components["pane_right"].filter = lambda: True
            self.layout_components["item_top_toggle"].text = '> log pane'

    def log_button_clicked(self):
        for tab in self.command_tabs.values():
            tab.is_selected = False
        self.redraw_app()

    def tab_button_clicked(self, command_name: str):
        for tab in self.command_tabs.values():
            tab.is_selected = False
        self.command_tabs[command_name].is_selected = True
        self.redraw_app()

    def exit(self):
        self.app.exit()

    def redraw_app(self):
        self.layout, self.layout_components = generate_layout_2(self.input_field, self.output_field, self.log_field,
                                                              self.right_pane_toggle, self.log_field_button,
                                                              self.timer,
                                                              self.process_usage)
        self.app.layout = self.layout
        self.app.invalidate()


    def tab_navigate_right(self):
        current_tabs = [t for t in self.command_tabs.values() if t.tab_index > 0]
        if not current_tabs:
            return
        selected_tab = [t for t in current_tabs if t.is_selected]
        if selected_tab:
            right_tab = [t for t in current_tabs if t.tab_index == selected_tab[0].tab_index + 1]
        else:
            right_tab = [t for t in current_tabs if t.tab_index == 1]
        if right_tab:
            self.tab_button_clicked(right_tab[0].name)

    def close_buton_clicked(self, command_name: str):
        self.command_tabs[command_name].button = None
        self.command_tabs[command_name].close_button = None
        self.command_tabs[command_name].output_field = None
        self.command_tabs[command_name].is_selected = False
        for tab in self.command_tabs.values():
            if tab.tab_index > self.command_tabs[command_name].tab_index:
                tab.tab_index -= 1
        self.command_tabs[command_name].tab_index = 0
        if self.command_tabs[command_name].task is not None:
            self.command_tabs[command_name].task.cancel()
            self.command_tabs[command_name].task = None
        self.redraw_app()

    