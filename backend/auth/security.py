"""Session cookies and the encryption of stored Kickbase tokens.

Passwords are never stored: they are sent to Kickbase once at login. What is kept is the token
Kickbase hands out, encrypted with a key from KBI_AUTH__SECRET_KEY or, without it, a key generated
once and kept in the data folder. The session cookie itself is only stored as a SHA-256 hash, so a
leaked database contains no usable cookies.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

log = logging.getLogger(__name__)

KEY_FILE = "secret.key"


class TokenCipher:
    def __init__(self, key: bytes):
        self._fernet = Fernet(key)

    @classmethod
    def from_settings(cls, secret: str | None, data_dir: Path) -> TokenCipher:
        if secret:
            ### Any string works as secret, it is stretched into a proper Fernet key
            return cls(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))

        path = data_dir / KEY_FILE
        if not path.exists():
            data_dir.mkdir(parents=True, exist_ok=True)
            key = Fernet.generate_key()
            try:
                ### Created readable for the owner only, and never overwritten
                descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(descriptor, "wb") as file:
                    file.write(key)
                log.info("Generated a new secret key in %s", path)
        return cls(path.read_bytes().strip())

    def encrypt(self, value: str) -> str:
        return self._fernet.encrypt(value.encode()).decode()

    def decrypt(self, value: str) -> str | None:
        """None if the value was encrypted with another key, e.g. after the secret changed."""
        try:
            return self._fernet.decrypt(value.encode()).decode()
        except InvalidToken:
            return None


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
