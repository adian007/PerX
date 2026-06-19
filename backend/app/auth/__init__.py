"""Authentication helpers — JWT, password hashing, and dependencies."""

from app.auth.dependencies import get_current_user, require_role
from app.auth.jwt import create_access_token, decode_access_token
from app.auth.passwords import hash_password, verify_password

__all__ = [
    "create_access_token",
    "decode_access_token",
    "get_current_user",
    "hash_password",
    "require_role",
    "verify_password",
]
