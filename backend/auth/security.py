import hashlib
import hmac
import os
import time

from jose import jwt


DEFAULT_INITIAL_PASSWORD = "Admin#123"
PASSWORD_HASH_ITERATIONS = 100_000
ACCESS_TOKEN_LIFETIME_SECONDS = 30 * 60
TOKEN_ISSUER = "intelligent-attendance-system"


def hash_password(password: str) -> str:
    salt = os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algorithm, salt, expected_digest = stored_hash.split("$", 2)
    except (AttributeError, ValueError):
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    actual_digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PASSWORD_HASH_ITERATIONS,
    ).hex()
    return hmac.compare_digest(actual_digest, expected_digest)


def _get_signing_key() -> str:
    signing_key = os.getenv("JWT_SECRET_KEY", "")
    if len(signing_key.encode("utf-8")) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY must be configured with at least 32 bytes."
        )
    return signing_key


def create_access_token(account_id: int) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": str(account_id),
            "iat": now,
            "exp": now + ACCESS_TOKEN_LIFETIME_SECONDS,
            "iss": TOKEN_ISSUER,
        },
        _get_signing_key(),
        algorithm="HS256",
    )


def decode_access_token(token: str) -> dict:
    return jwt.decode(
        token,
        _get_signing_key(),
        algorithms=["HS256"],
        issuer=TOKEN_ISSUER,
        options={"require": ["sub", "iat", "exp", "iss"]},
    )
