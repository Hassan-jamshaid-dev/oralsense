import base64
import hashlib
import hmac
import secrets

PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128

SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_SALT_BYTES = 16
SCRYPT_DKLEN = 64


def _scrypt(password: str, salt: bytes, n: int, r: int, p: int, dklen: int) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=n, r=r, p=p, dklen=dklen, maxmem=64 * 1024 * 1024
    )


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SCRYPT_SALT_BYTES)
    derived = _scrypt(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P, SCRYPT_DKLEN)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    hash_b64 = base64.b64encode(derived).decode("ascii")
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt_b64}${hash_b64}"


def _parse_password_hash(stored_hash: str) -> tuple[bytes, bytes] | None:
    """Return salt and digest only for hashes this app writes. Anything else is malformed."""
    try:
        algorithm, n_raw, r_raw, p_raw, salt_b64, hash_b64 = stored_hash.split("$")
        salt = base64.b64decode(salt_b64, validate=True)
        expected = base64.b64decode(hash_b64, validate=True)
        well_formed = (
            algorithm == "scrypt"
            and int(n_raw) == SCRYPT_N
            and int(r_raw) == SCRYPT_R
            and int(p_raw) == SCRYPT_P
            and len(salt) == SCRYPT_SALT_BYTES
            and len(expected) == SCRYPT_DKLEN
        )
    except (ValueError, TypeError):
        return None
    if not well_formed:
        return None
    return salt, expected


def verify_password(password: str, stored_hash: str) -> bool:
    """Compare in constant time. A malformed stored hash fails closed and still costs one scrypt."""
    parsed = _parse_password_hash(stored_hash)
    if parsed is None:
        salt = b"\x00" * SCRYPT_SALT_BYTES
        expected = b"\x00" * SCRYPT_DKLEN
    else:
        salt, expected = parsed
    try:
        derived = _scrypt(password, salt, SCRYPT_N, SCRYPT_R, SCRYPT_P, SCRYPT_DKLEN)
    except (ValueError, TypeError):
        return False
    matched = hmac.compare_digest(derived, expected)
    return parsed is not None and matched


# Verified against when the email is unknown so both login paths cost one scrypt run.
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(16))


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def generate_csrf_token() -> str:
    # Readable by the SPA (returned on /auth/me). Not a session credential.
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
