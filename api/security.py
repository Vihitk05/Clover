import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Tuple

import bcrypt
import jwt

from config.settings import config


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(
    subject: str,
    extra: Dict[str, Any] | None = None,
    expires_minutes: int | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    expiry_minutes = expires_minutes or config.JWT_ACCESS_TOKEN_EXPIRES_MINUTES
    payload: Dict[str, Any] = {
        "sub": subject,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=expiry_minutes)).timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)


def create_refresh_token(
    subject: str,
    extra: Dict[str, Any] | None = None,
    expires_days: int | None = None,
) -> Tuple[str, str, datetime]:
    now = datetime.now(timezone.utc)
    expiry_days = expires_days or config.JWT_REFRESH_TOKEN_EXPIRES_DAYS
    expiry = now + timedelta(days=expiry_days)

    raw_token = secrets.token_urlsafe(48)
    payload: Dict[str, Any] = {
        "sub": subject,
        "type": "refresh",
        "jti": secrets.token_hex(16),
        "rt": raw_token,
        "iat": int(now.timestamp()),
        "exp": int(expiry.timestamp()),
    }
    if extra:
        payload.update(extra)

    encoded = jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)
    token_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return encoded, token_hash, expiry


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, config.JWT_SECRET_KEY, algorithms=[config.JWT_ALGORITHM])


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
