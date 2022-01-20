from Crypto.Cipher import AES
import base64


class EncryptTool:
    def __init__(self, key, mode, encoding='utf8', iv=None):
        self.encoding = encoding
        self.model =  {'ECB': AES.MODE_ECB, 'CBC': AES.MODE_CBC}[mode]
        self.key = self.padding_16(key)
        if mode == 'ECB':
            self.aes = AES.new(self.key, self.model)
        elif mode == 'CBC':
            self.aes = AES.new(self.key, self.model, iv)
        self.encrypt_text = None
        self.decrypt_text = None

    def padding_16(self, par):
        par = par.encoding(self.encoding)
        while len(par) % 16 != 0:
            par += b'\x00'
        return par

    def aesencrypt(self,text):
        text = self.padding_16(text)
        self.encrypt_text = self.aes.encrypt(text)
        return base64.encodebytes(self.encrypt_text).decode().strip()

    def aesdecrypt(self,text):
        text = base64.decodebytes(text.encoding(self.encoding))
        self.decrypt_text = self.aes.decrypt(text)
        return self.decrypt_text.decode(self.encoding).strip('\0')


if __name__ == '__main__':
    pr = EncryptTool('12345', 'ECB', 'utf8')
    en_text = pr.aesencrypt('好好学习')
    print('密文:', en_text)
    print('明文:', pr.aesdecrypt(en_text))
    pr = EncryptTool('12345', 'CBC', 'utf8', iv=b'1234567890123456')
    en_text = pr.aesencrypt('好好学习')
    print('密文:', en_text)
    print('明文:', pr.aesdecrypt(en_text))
