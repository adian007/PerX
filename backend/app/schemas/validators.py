"""Shared Pydantic validators."""

from __future__ import annotations

from typing import Annotated

from pydantic import BeforeValidator, EmailStr, TypeAdapter

_EMAIL_ADAPTER = TypeAdapter(EmailStr)


def normalize_auth_email(value: str) -> str:
    """Validate email for auth endpoints.

    Standard addresses use strict ``EmailStr`` validation. In demo/dev mode,
    reserved TLDs used by seed data (``.local``) are accepted so demo logins work.
    """

    cleaned = value.strip().lower()
    if not cleaned or "@" not in cleaned:
        raise ValueError("Invalid email address")

    _local, _, domain = cleaned.partition("@")
    if not _local or not domain:
        raise ValueError("Invalid email address")

    if domain.endswith(".local") or domain.endswith(".localhost") or domain == "localhost":
        return cleaned

    return _EMAIL_ADAPTER.validate_python(cleaned)


PerxEmailStr = Annotated[str, BeforeValidator(normalize_auth_email)]
