"""bcrypt password and refresh-token hashing."""

from __future__ import annotations

import bcrypt

_BCRYPT_ROUNDS = 12


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with bcrypt (cost factor 12)."""

    digest = bcrypt.hashpw(plain_password.encode("utf-8"), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS))
    return digest.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True when the plaintext password matches the stored hash."""

    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def hash_token(token: str) -> str:
    """Hash a refresh token for storage (bcrypt, cost factor 12)."""

    digest = bcrypt.hashpw(token.encode("utf-8"), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS))
    return digest.decode("utf-8")


def verify_token(plain_token: str, hashed_token: str) -> bool:
    """Return True when a plaintext refresh token matches the stored hash."""

    return bcrypt.checkpw(plain_token.encode("utf-8"), hashed_token.encode("utf-8"))
