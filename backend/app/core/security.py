import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import AppException, ErrorCode


def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception:
        return False


def create_access_token(user_id: uuid.UUID, role: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token containing user_id, role, and expiration."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "user_id": str(user_id),
        "role": role,
        "exp": expire
    }

    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate JWT access token."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise AppException(
            status_code=401,
            code=ErrorCode.AUTH_TOKEN_EXPIRED,
            message="Token has expired."
        )
    except (jwt.InvalidTokenError, Exception):
        raise AppException(
            status_code=401,
            code=ErrorCode.AUTH_TOKEN_INVALID,
            message="Invalid authentication token."
        )
