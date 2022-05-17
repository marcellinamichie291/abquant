#!/usr/bin/env python

import asyncio
import logging
import os.path
from typing import Optional, Dict
from argparse import ArgumentParser

from prompt_toolkit.completion.word_completer import WordCompleter

from abquantui.abquant_cli import AbquantCLI
from abquantui.commands import __all__ as commands
from abquantui.commands.command_parser import load_parser
from abquantui.config_helpers import parse_config
from abquantui.exceptions import ArgumentParserError
from abquantui.keybindings import load_key_bindings
from abquantui.strategy_lifecycle import StrategyLifecycle

s_logger = None


class AbquantApplication(*commands):
    _main_app: Optional["AbquantApplication"] = None

    @classmethod
    def logger(cls) -> logging.Logger:
        global s_logger
        if s_logger is None:
            s_logger = logging.getLogger(__name__)
        return s_logger

    @classmethod
    def main_application(cls, config_file, strategy_lifecycle_class) -> "AbquantApplication":
        if cls._main_app is None:
            cls._main_app = AbquantApplication(config_file, strategy_lifecycle_class)
        return cls._main_app

    def __init__(self, config_file: str,
                 strategy_lifecycle_class: StrategyLifecycle):
        self._config = None
        self.strategy_lifecycle_class = strategy_lifecycle_class
        self._config: Dict = parse_config(config_file)
        logging.info(self._config)
        self.strategy_name = self._config.get('strategy_name')
        self.config_path = config_file
        self.log_file = os.path.join(self._config.get('log_path') if 'log_path' in self._config else 'logs',
                                     self.strategy_name + '.log')
        self.strategy_lifecycle: StrategyLifecycle = None
        self.ev_loop: asyncio.BaseEventLoop = asyncio.get_event_loop()
        self._parser: ArgumentParser = load_parser(self)
        self.placeholder_mode = False
        self.completer = WordCompleter(
            [
                "connect",
                "start",
                "stop",
                "status",
                "config",
                'shutdown'
            ],
            ignore_case=True,
        )
        self.app = AbquantCLI(
            input_handler=self._handle_command,
            bindings=load_key_bindings(self),
            completer=self.completer,
            strategy_name=self.strategy_name,
            config_file=self.config_path,
            log_file=self.log_file
        )

    def _notify(self, msg: str):
        self.app.log(msg)

    async def cls_display_delay(self, lines, delay=0.5):
        self.app.output_field.buffer.save_to_undo_stack()
        self.app.log("".join(lines), save_log=False)
        await asyncio.sleep(delay)
        self.app.output_field.buffer.undo()

    def stop_live_update(self):
        if self.app.live_updates is True:
            self.app.live_updates = False

    def _handle_command(self, raw_command: str):

        if not raw_command or raw_command.strip() == '' or self.placeholder_mode:
            return
        if self.app.live_updates:
            self.logger().info("No command is processed, Press escape to stop live updates first!")
            return
        try:
            args = self._parser.parse_args(args=raw_command.split())
            kwargs = vars(args)
            f = args.func
            del kwargs["func"]
            f(**kwargs)
        except Exception as e:
            self._notify(str(e))
            self.logger().error(e, exc_info=True)

    async def run(self):
        self.strategy_lifecycle = self.strategy_lifecycle_class(self._config)
        await self.app.run()


if __name__ == '__main__':
    parser = load_parser(None)
    parser.parse_args(['a'])
