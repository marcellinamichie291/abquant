import os
import argparse
from abquantui.encryption import encrypt, decrypt


def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--encrypt', type=str, required=False,
                        help='encrypt text')
    parser.add_argument('-d', '--decrypt', type=str, required=False,
                        help='decrypt text')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    default = "abquanT%go2moon!"
    abpwd = os.getenv("ABPWD", default)
    if abpwd == default:
        print(f"{'-'*16} SET ABPWD={abpwd} {'-'*16}")
        print(f"Usage: ABPWD=YourPassword python encrypt_tool.py -e YourKey\n{'-'*60}")
    if len(abpwd) > 32:
        print('Your password is too long (<=32)')
        exit(1)
    etargs = parse()
    if etargs.encrypt:
        dtext = encrypt(etargs.encrypt, abpwd)
        print(f'Before encrypt:\t{etargs.encrypt}')
        print(f'After encrypt:\t{dtext}')
    if etargs.decrypt:
        print(f'Before decrypt:\t{etargs.decrypt}')
        print(f'After decrypt:\t{decrypt(etargs.decrypt, abpwd)}')
