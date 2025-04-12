import urandom


def xor_encrypt(data: bytes, key: bytes) -> bytes:
    return bytes([b ^ key[i % len(key)] for i, b in enumerate(data)])


def generate_random_key(length=16):
    return bytes([urandom.getrandbits(8) for _ in range(length)])


def random_name():
    import ubinascii
    base = ''.join(chr(65 + urandom.getrandbits(5)) for _ in range(8))
    digits = ''.join(str(urandom.getrandbits(4)) for _ in range(3))
    del ubinascii
    return base + digits
