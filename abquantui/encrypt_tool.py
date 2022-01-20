import os
from Crypto.Cipher import AES
import base64
import argparse


def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('-e', '--encrypt', type=str, required=False,
                        help='encrypt text')
    parser.add_argument('-d', '--decrypt', type=str, required=False,
                        help='decrypt text')
    args = parser.parse_args()
    return args


class EncryptTool:
    def __init__(self, password, mode, encoding='utf8', iv=None):
        self.encoding = encoding
        self.mode =  {'ECB': AES.MODE_ECB, 'CBC': AES.MODE_CBC}[mode]
        self.key = self.padding_16(password)
        self.iv = iv

    def padding_16(self, s):
        s = s.encode(self.encoding)
        return s + ((16 - len(s) % 16) * b'\x00')

    def aesencrypt(self, text):
        text = self.padding_16(text)
        if self.mode == AES.MODE_CBC:
            aes = AES.new(self.key, self.mode, self.iv)
        elif self.mode == AES.MODE_ECB:
            aes = AES.new(self.key, self.mode)
        encrypt_text = aes.encrypt(text)
        return base64.encodebytes(encrypt_text).decode().strip()

    def aesdecrypt(self, text):
        text = base64.decodebytes(text.encode(self.encoding))
        if self.mode == AES.MODE_CBC:
            aes = AES.new(self.key,self.mode,self.iv)
        elif self.mode == AES.MODE_ECB:
            aes = AES.new(self.key,self.mode)
        decrypt_text = aes.decrypt(text)
        decrypt_text = decrypt_text.decode(self.encoding).strip('\0')
        return decrypt_text


if __name__ == '__main__':
    abpwd = os.getenv("ABPWD", "abquanT%go2moon!")
    # print(f"******ABPWD={abpwd}******")
    pr = EncryptTool(abpwd, 'ECB', 'utf8')
    etargs = parse()
    if etargs.encrypt:
        dtext = pr.aesencrypt(etargs.encrypt)
        print(f'Before encrypt:\t{etargs.encrypt}')
        print(f'After encrypt:\t{dtext}')
    if etargs.decrypt:
        print(f'Before decrypt:\t{etargs.decrypt}')
        print(f'After decrypt:\t{pr.aesdecrypt(etargs.decrypt)}')
