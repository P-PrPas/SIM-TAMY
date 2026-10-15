"""Learner session token (API_DESIGN 3): opaque, shown once, only its sha256 is stored."""

import hashlib
import secrets


def new_token() -> str:
    return "st_" + secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
