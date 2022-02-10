from Crypto.Cipher import AES
import base64


class EncryptTool:
    def __init__(self, password, mode='ECB', encoding='utf8', iv=None):
        self.encoding = encoding
        self.mode =  {'ECB': AES.MODE_ECB, 'CBC': AES.MODE_CBC}[mode] if mode else AES.MODE_ECB
        self.password = self.padding_16(password)
        self.iv = iv.encode(encoding) if iv else None

    def padding_16(self, s):
        s = s.encode(self.encoding)
        return s + ((16 - len(s) % 16) * b'\x00') if len(s) % 16 != 0 else s

    def aesencrypt(self, text):
        text = text.replace('\n', '')
        text = self.padding_16(text)
        if self.mode == AES.MODE_CBC:
            aes = AES.new(self.password, self.mode, self.iv)
        elif self.mode == AES.MODE_ECB:
            aes = AES.new(self.password, self.mode)
        encrypt_text = aes.encrypt(text)
        return str(base64.b64encode(encrypt_text), encoding=self.encoding).strip()

    def aesdecrypt(self, text):
        text = base64.b64decode(text.encode(self.encoding))
        if self.mode == AES.MODE_CBC:
            aes = AES.new(self.password, self.mode, self.iv)
        elif self.mode == AES.MODE_ECB:
            aes = AES.new(self.password, self.mode)
        decrypt_text = aes.decrypt(text)
        decrypt_text = decrypt_text.decode(self.encoding).strip('\0')
        return decrypt_text


def encrypt(text, password='abquanT%go2moon!'):
    if not text:
        return ''
    et = EncryptTool(password)
    return et.aesencrypt(text)

def decrypt(text, password='abquanT%go2moon!'):
    if not text:
        return ''
    et = EncryptTool(password)
    return et.aesdecrypt(text)
