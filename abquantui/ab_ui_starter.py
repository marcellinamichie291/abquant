import asyncio
import os
import sys

from abquantui.strategy_lifecycle import StrategyLifecycle

from typing import List, Coroutine

from abquantui.abquant_application import AbquantApplication
from abquantui.config_helpers import setup_logging, parse_yaml
from hummingbot.client.ui.stdout_redirection import patch_stdout
from hummingbot.client.ui.style import dialog_style
from prompt_toolkit.shortcuts import message_dialog


def setup_log_with_config(config_path: str):
    config = parse_yaml(config_path)
    strategy_name = config.get('strategy_name')
    log_file = os.path.join(config.get('log_path'), strategy_name + '.log')
    setup_logging(log_file)


async def main(config_path: str, strategy_class: StrategyLifecycle):
    main_app = AbquantApplication.main_application(config_path, strategy_class)

    tasks: List[Coroutine] = [main_app.run()]
    with patch_stdout(log_field=main_app.app.log_field):
        setup_log_with_config(config_path)
        await asyncio.gather(*tasks)


def ab_ui_starter(config_path, strategy_class):
    message_dialog(
        title="Welcome",
        text="Welcome to use abquant, enjoy your trading life!",
        style=dialog_style
    ).run()
    asyncio.run(main(config_path, strategy_class))
