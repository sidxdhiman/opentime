import hashlib
import secrets

import bcrypt


def _digest(password: str) -> bytes:
    # Pre-hash so bcrypt's 72-byte input limit never applies.
    return hashlib.sha256(password.encode("utf-8")).digest()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_digest(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(_digest(plain_password), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
