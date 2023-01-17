from nacl.signing import SigningKey, VerifyKey


def sign(skey_hex: str, message_hex: str):
    skey = SigningKey(bytes.fromhex(skey_hex))

    signed = skey.sign(bytes.fromhex(message_hex))

    return signed


def verify(vkey_hex: str, message_hex: str, signature_hex: str):
    vkey = VerifyKey(bytes.fromhex(vkey_hex))

    return vkey.verify(
        bytes.fromhex(message_hex),
        bytes.fromhex(signature_hex),
    )