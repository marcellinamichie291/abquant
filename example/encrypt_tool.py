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
    abpwd = os.getenv("ABPWD", "abquanT%go2moon!")
    print(f"******ABPWD={abpwd}******")
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
