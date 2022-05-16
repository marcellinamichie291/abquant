import argparse
# parser = argparse.ArgumentParser(add_help=False)
# parser.add_argument('subcommand',nargs=1, help='foo help')
# parser.add_argument('--key', help='bar help')
# parser.add_argument('--value', help='bar help')
# args = parser.parse_args()
# print(args)

parser = argparse.ArgumentParser(prog="", add_help=False)
subparsers = parser.add_subparsers()

config_parser = subparsers.add_parser("config", help="None", )
config_parser.add_argument('subcommand', nargs="?", choices=['reload', 'update'])
config_parser.add_argument('key', nargs="?", help='config key to be updated')
config_parser.add_argument('value', nargs="?", help='config value to be udpated')
config_parser.add_argument('--save', nargs="?", help='config value to be udpated')


status_parser = subparsers.add_parser("status", help="None", )
status_parser.add_argument('--live', default=False, action="store_true")

args = parser.parse_args(['config', 'update'])
print(vars(args))

