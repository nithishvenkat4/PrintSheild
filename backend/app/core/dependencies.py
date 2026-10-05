import uuid
from typing import Optional
from fastapi import Depends, Header
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User, UserRole
from app.core.security import decode_access_token
from app.core.exceptions import AppException, ErrorCode


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """Extract and validate JWT Bearer token and return active user."""
    if not authorization:
        raise AppException(
            status_code=401,
            code=ErrorCode.AUTH_TOKEN_INVALID,
            message="Authorization header missing."
        )

    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise AppException(
            status_code=401,
            code=ErrorCode.AUTH_TOKEN_INVALID,
            message="Invalid Authorization header format. Expected 'Bearer <token>'."
        )

    token = parts[1]
    payload = decode_access_token(token)

    user_id_str = payload.get("user_id")
    if not user_id_str:
        raise AppException(
            status_code=401,
            code=ErrorCode.AUTH_TOKEN_INVALID,
            message="Token payload invalid."
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise AppException(
            status_code=401,
            code=ErrorCode.AUTH_TOKEN_INVALID,
            message="Token contains invalid user identity."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise AppException(
            status_code=401,
            code=ErrorCode.AUTH_TOKEN_INVALID,
            message="User not found."
        )

    if not user.is_active:
        raise AppException(
            status_code=403,
            code=ErrorCode.AUTH_INSUFFICIENT_ROLE,
            message="User account is inactive."
        )

    return user


def require_customer(current_user: User = Depends(get_current_user)) -> User:
    """Require user to be a customer (or admin)."""
    if current_user.role not in (UserRole.CUSTOMER, UserRole.ADMIN):
        raise AppException(
            status_code=403,
            code=ErrorCode.AUTH_INSUFFICIENT_ROLE,
            message="Access forbidden: Customer role required."
        )
    return current_user


def require_shop_owner(current_user: User = Depends(get_current_user)) -> User:
    """Require user to be a shop owner (or admin)."""
    if current_user.role not in (UserRole.SHOP_OWNER, UserRole.ADMIN):
        raise AppException(
            status_code=403,
            code=ErrorCode.AUTH_INSUFFICIENT_ROLE,
            message="Access forbidden: Shop owner role required."
        )
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require user to be an administrator."""
    if current_user.role != UserRole.ADMIN:
        raise AppException(
            status_code=403,
            code=ErrorCode.AUTH_INSUFFICIENT_ROLE,
            message="Access forbidden: Administrator role required."
        )
    return current_user


# Aliases and helpers
get_current_active_user = get_current_user


def require_role(required_role: UserRole):
    def role_dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != required_role and current_user.role != UserRole.ADMIN:
            raise AppException(
                status_code=403,
                code=ErrorCode.AUTH_INSUFFICIENT_ROLE,
                message=f"Access forbidden: {required_role.value} role required."
            )
        return current_user
    return role_dependency

