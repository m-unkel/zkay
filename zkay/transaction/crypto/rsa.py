import os
import sys
from typing import Tuple, Optional, List

from Crypto.Cipher import PKCS1_OAEP
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes

import zkay.config as cfg
from zkay.transaction.interface import PrivateKeyValue, PublicKeyValue, KeyPair, CipherValue, ZkayBlockchainInterface, RandomnessValue
from zkay.transaction.interface import ZkayCryptoInterface


# persistent_locals2 has been co-authored with Andrea Maffezzoli
# http://code.activestate.com/recipes/577283-decorator-to-expose-local-variables-of-a-function-/
# (hack to get local variables of called library function, used to extract randomness)
class PersistentLocals(object):
    def __init__(self, func):
        self._locals = {}
        self.func = func

    def __call__(self, *args, **kwargs):
        def tracer(frame, event, arg):
            if event=='return':
                self._locals = frame.f_locals.copy()

        # tracer is activated on next call, return or exception
        sys.setprofile(tracer)
        try:
            # trace the function call
            res = self.func(*args, **kwargs)
        finally:
            # disable tracer and replace with old one
            sys.setprofile(None)
        return res

    def clear_locals(self):
        self._locals = {}

    @property
    def locals(self):
        return self._locals


class RSACrypto(ZkayCryptoInterface):
    key_file = os.path.join(cfg.config_dir, 'rsa_keypair.bin')
    default_exponent = 65537 # == 0x10001

    def __init__(self, conn: ZkayBlockchainInterface, key_dir: str = os.path.dirname(os.path.realpath(__file__))):
        super().__init__(conn, key_dir)

    def _generate_or_load_key_pair(self) -> KeyPair:
        if not os.path.exists(self.key_file):
            print(f'Key pair not found, generating new {cfg.rsa_key_bits} bit rsa key pair...')
            key = RSA.generate(cfg.rsa_key_bits, e=self.default_exponent)
            with open(self.key_file, 'wb') as f:
                f.write(key.export_key())
            print('done')
        else:
            print(f'Key pair found, loading from file {self.key_file}')
            with open(self.key_file, 'rb') as f:
                key = RSA.import_key(f.read())

        modulus = key.publickey().n
        return KeyPair(PublicKeyValue(self.serialize_bigint(modulus, cfg.rsa_key_bytes)), PrivateKeyValue(key))

    def _enc(self, plain: int, pk: int, rnd: Optional[Tuple[int, ...]]) -> Tuple[List[int], List[int]]:
        pub_key = RSA.construct((pk, self.default_exponent))

        if rnd is None:
            randfunc = get_random_bytes
        else:
            randbytes = self.unpack_to_byte_array(rnd, cfg.rsa_rnd_bytes)
            randfunc = lambda n: randbytes
        encrypt = PersistentLocals(PKCS1_OAEP.new(pub_key, hashAlgo=SHA256, randfunc=randfunc).encrypt)

        cipher = self.pack_byte_array(encrypt(plain.to_bytes(31, byteorder='big')))
        rnd = self.pack_byte_array(encrypt.locals['ros'])

        return cipher, rnd

    def _dec(self, cipher: Tuple[int, ...], sk: RSA.RsaKey) -> Tuple[int, List[int]]:
        if cipher == CipherValue()[:]:
            # uninitialized value
            return 0, RandomnessValue()[:]
        else:
            decrypt = PersistentLocals(PKCS1_OAEP.new(sk, hashAlgo=SHA256).decrypt)
            plain = int.from_bytes(decrypt(self.unpack_to_byte_array(cipher, cfg.rsa_key_bytes)), byteorder='big')
            rnd = self.pack_byte_array(decrypt.locals['seed'])

            return plain, rnd
