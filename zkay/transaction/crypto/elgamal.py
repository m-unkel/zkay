import os
from typing import Tuple, List, Any, Union

from Crypto.Random.random import randrange

from zkay.config import cfg, zk_print
from zkay.transaction.crypto import babyjubjub
from zkay.transaction.crypto.params import CryptoParams
from zkay.transaction.interface import ZkayHomomorphicCryptoInterface
from zkay.transaction.types import KeyPair, CipherValue, PrivateKeyValue, PublicKeyValue


class ElgamalCrypto(ZkayHomomorphicCryptoInterface):
    params = CryptoParams('elgamal')

    def _generate_or_load_key_pair(self, address: str) -> KeyPair:
        key_file = os.path.join(cfg.data_dir, 'keys', f'elgamal_{self.params.key_bits}_{address}.bin')
        os.makedirs(os.path.dirname(key_file), exist_ok=True)
        if not os.path.exists(key_file):
            zk_print(f'Key pair not found, generating new ElGamal secret...')
            pk, sk = self._generate_key_pair()
            self._write_key_pair(key_file, pk, sk)
            zk_print('Done')
        else:
            # Restore saved key pair
            zk_print(f'ElGamal secret found, loading from file {key_file}')
            pk, sk = self._read_key_pair(key_file)

        return KeyPair(PublicKeyValue(pk, params=self.params), PrivateKeyValue(sk))

    def _write_key_pair(self, key_file: str, pk: List[int], sk: int):
        with open(key_file, 'wb') as f:
            for p in pk:
                f.write(p.to_bytes(self.params.cipher_chunk_size, byteorder='big'))
            f.write(sk.to_bytes(self.params.cipher_chunk_size, byteorder='big'))

    def _read_key_pair(self, key_file: str) -> Tuple[List[int], int]:
        with open(key_file, 'rb') as f:
            pkx = int.from_bytes(f.read(self.params.cipher_chunk_size), byteorder='big')
            pky = int.from_bytes(f.read(self.params.cipher_chunk_size), byteorder='big')
            sk = int.from_bytes(f.read(self.params.cipher_chunk_size), byteorder='big')
        return [pkx, pky], sk

    def _generate_key_pair(self) -> Tuple[List[int], int]:
        sk = randrange(babyjubjub.CURVE_ORDER)
        pk = babyjubjub.Point.GENERATOR * babyjubjub.Fr(sk)
        return [pk.u.s, pk.v.s], sk

    def _enc(self, plain: int, _: int, target_pk: int) -> Tuple[List[int], List[int]]:
        pk = self.serialize_pk(target_pk, self.params.key_bytes)
        r = randrange(babyjubjub.CURVE_ORDER)
        cipher_chunks = self._enc_with_rand(plain, r, pk)
        return cipher_chunks, [r]

    def _dec(self, cipher: Tuple[int, ...], sk: Any) -> Tuple[int, List[int]]:
        c1 = babyjubjub.Point(babyjubjub.Fq(cipher[0]), babyjubjub.Fq(cipher[1]))
        c2 = babyjubjub.Point(babyjubjub.Fq(cipher[2]), babyjubjub.Fq(cipher[3]))
        shared_secret = c1 * babyjubjub.Fr(sk)
        plain_embedded = c2 + shared_secret.negate()
        plain = self._de_embed(plain_embedded)

        # TODO randomness misused for the secret key, which is an extremely ugly hack...
        return plain, [sk]

    def _de_embed(self, plain_embedded: babyjubjub.Point) -> int:
        # TODO implement more efficient baby-step giant-step algorithm
        for plain in range(0, 100):
            check_embedded = babyjubjub.Point.GENERATOR * babyjubjub.Fr(plain)
            if check_embedded.u.s == plain_embedded.u.s and check_embedded.v.s == plain_embedded.v.s:
                return plain
        raise Exception("could not de-embed message")

    def do_op(self, op: str, public_key: List[int], *args: Union[CipherValue, int]) -> List[int]:
        # TODO handle uninitialized ciphertext 0
        if op == '+':
            assert isinstance(args[0], CipherValue) and isinstance(args[1], CipherValue)
            c1 = babyjubjub.Point(babyjubjub.Fq(args[0][0]), babyjubjub.Fq(args[0][1]))
            c2 = babyjubjub.Point(babyjubjub.Fq(args[0][2]), babyjubjub.Fq(args[0][3]))
            d1 = babyjubjub.Point(babyjubjub.Fq(args[1][0]), babyjubjub.Fq(args[1][1]))
            d2 = babyjubjub.Point(babyjubjub.Fq(args[1][2]), babyjubjub.Fq(args[1][3]))
            e1 = c1 + d1
            e2 = c2 + d2
            return [e1.u.s, e1.v.s, e2.u.s, e2.v.s]
        else:
            raise ValueError(f'Unsupported operation {op}')

    def _enc_with_rand(self, plain: int, random: int, pk: List[int]) -> List[int]:
        plain_embedded = babyjubjub.Point.GENERATOR * babyjubjub.Fr(plain)
        shared_secret = babyjubjub.Point(babyjubjub.Fq(pk[0]), babyjubjub.Fq(pk[1])) * babyjubjub.Fr(random)
        c1 = babyjubjub.Point.GENERATOR * babyjubjub.Fr(random)
        c2 = plain_embedded + shared_secret
        return [c1.u.s, c1.v.s, c2.u.s, c2.v.s]