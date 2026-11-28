import secrets

# Ambiguous glyphs are omitted so a code can be read aloud. The value is random:
# it is not derived from a name, a label, or the internal id.
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_PREFIX = "RS-"
_BODY_LENGTH = 8

CODE_ATTEMPTS = 8


def generate_participant_code() -> str:
    body = "".join(secrets.choice(_ALPHABET) for _ in range(_BODY_LENGTH))
    return f"{_PREFIX}{body}"
