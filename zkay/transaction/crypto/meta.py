cryptoparams = {'dummy': {
    'key_bits': 248,
    'rnd_bytes': 31
}, 'rsa_oaep': {
    'key_bits': 2048,
    'rnd_bytes': 32
}, 'rsa_pkcs1_5': {
    'key_bits': 2048,
    'rnd_bytes': 221 # for 256 - 3 - plainbytes (32 byte plaintext, for now fixed)
}}
