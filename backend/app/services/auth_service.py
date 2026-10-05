from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.models.audit_log import AuditAction
from app.core.security import hash_password, verify_password, create_access_token
from app.core.exceptions import AppException, ErrorCode
from app.services.audit_service import audit_service


class AuthService:
    @staticmethod
    def register(
        db: Session,
        name: str,
        email: str,
        password: str,
        role: Optional[UserRole] = None,
        ip_address: Optional[str] = None
    ) -> User:
        # Check if email is already registered
        existing_user = db.query(User).filter(User.email == email.lower()).first()
        if existing_user:
            raise AppException(
                status_code=400,
                code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                message="An account with this email already exists."
            )

        # Protect against arbitrary ADMIN escalation (Section 130)
        target_role = role or UserRole.CUSTOMER
        if target_role == UserRole.ADMIN:
            raise AppException(
                status_code=403,
                code=ErrorCode.AUTH_INSUFFICIENT_ROLE,
                message="Administrator accounts cannot be self-registered."
            )

        hashed = hash_password(password)
        new_user = User(
            name=name,
            email=email.lower(),
            password_hash=hashed,
            role=target_role,
            is_active=True
        )
        db.add(new_user)
        db.flush()

        audit_service.log_event(
            db=db,
            action=AuditAction.USER_REGISTERED,
            actor_id=new_user.id,
            ip_address=ip_address,
            metadata={"email": new_user.email, "role": new_user.role.value}
        )
        db.commit()
        db.refresh(new_user)
        return new_user

    @staticmethod
    def login(
        db: Session,
        email: str,
        password: str,
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        user = db.query(User).filter(User.email == email.lower()).first()
        if not user or not verify_password(password, user.password_hash):
            raise AppException(
                status_code=401,
                code=ErrorCode.AUTH_INVALID_CREDENTIALS,
                message="Invalid email or password."
            )

        if not user.is_active:
            raise AppException(
                status_code=403,
                code=ErrorCode.AUTH_INSUFFICIENT_ROLE,
                message="User account is inactive."
            )

        token = create_access_token(user_id=user.id, role=user.role.value)

        audit_service.log_event(
            db=db,
            action=AuditAction.USER_LOGIN,
            actor_id=user.id,
            ip_address=ip_address,
            metadata={"email": user.email}
        )
        db.commit()

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": user
        }


auth_service = AuthService()
