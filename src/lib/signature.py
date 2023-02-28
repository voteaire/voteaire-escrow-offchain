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


# Function that should enforce the standard for a string
# It should make sure that the string is in the follwing format:
# "<question1choice1>,<question1choice2>,...|<question2choice1>,<question2choice2>,...|..."
# where everything inside <> should be an integer
def enforce_standard(results: str) -> bool:
    for question in results.split("|"):
        for choice in question.split(","):
            try:
                int(choice)
            except ValueError:
                return False

    return True
