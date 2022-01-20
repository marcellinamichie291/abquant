from Crypto.Cipher import AES
import base64


class EncryptTool:
    def __init__(self, key, mode, encoding='utf8', iv=None):
        self.encoding = encoding
        self.mode =  {'ECB': AES.MODE_ECB, 'CBC': AES.MODE_CBC}[mode]
        self.key = self.padding_16(key)
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
    pr = EncryptTool('12345', 'ECB', 'utf8')
    en_text = pr.aesencrypt('神秘峡谷6$8stay')
    print('密文:', en_text)
    print('明文:', pr.aesdecrypt(en_text))
    pr2 = EncryptTool('12345', 'CBC', 'utf8', iv=b'1234567890123456')
    en_text = pr2.aesencrypt('神秘峡谷6$8stay')
    print('密文:', en_text)
    print('明文:', pr2.aesdecrypt(en_text))
