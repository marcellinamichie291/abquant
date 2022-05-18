# sub-command functions
import argparse
from typing import List

from abquantui.exceptions import ArgumentParserError


class ThrowingArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        raise ArgumentParserError(message)

    def exit(self, status=0, message=None):
        pass

    def print_help(self, file=None):
        pass

    @property
    def subparser_action(self):
        for action in self._actions:
            if isinstance(action, argparse._SubParsersAction):
                return action

    @property
    def commands(self) -> List[str]:
        return list(self.subparser_action._name_parser_map.keys())

    def subcommands_from(self, top_level_command: str) -> List[str]:
        parser: argparse.ArgumentParser = self.subparser_action._name_parser_map.get(top_level_command)
        if parser is None:
            return []
        subcommands = parser._optionals._option_string_actions.keys()
        filtered = list(filter(lambda sub: sub.startswith("--") and sub != "--help", subcommands))
        return filtered


def load_parser(app):
    parser = ThrowingArgumentParser(prog="", add_help=False)
    subparsers = parser.add_subparsers()

    config_parser = subparsers.add_parser("config", help="None", )
    config_parser.add_argument('subcommand', nargs="?", choices=['reload', 'update', 'yaml'])
    config_parser.add_argument('key', nargs="?", help='config key to be updated')
    config_parser.add_argument('value', nargs="?", help='config value to be udpated')
    config_parser.set_defaults(func=app.config)

    connect_parser = subparsers.add_parser("connect")
    connect_parser.set_defaults(func=app.connect)

    start_parser = subparsers.add_parser("start")
    start_parser.set_defaults(func=app.start)

    stop_parser = subparsers.add_parser("stop")
    stop_parser.set_defaults(func=app.stop)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument('--live', default=False, action="store_true")
    status_parser.set_defaults(func=app.status)

    shutdown_parser = subparsers.add_parser("shutdown")
    shutdown_parser.set_defaults(func=app.shutdown)

    help_parser = subparsers.add_parser("help")
    help_parser.set_defaults(func=app.help)
    return parser
