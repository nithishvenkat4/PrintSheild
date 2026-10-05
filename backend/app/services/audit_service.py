import uuid
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog, AuditAction


class AuditService:
    @staticmethod
    def log_event(
        db: Session,
        action: str,
        actor_id: Optional[uuid.UUID] = None,
        job_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLog:
        """Create and persist an audit log record."""
        # Sanitize metadata to prevent logging sensitive secrets
        safe_metadata = {}
        if metadata:
            for k, v in metadata.items():
                if k.lower() not in ("password", "password_hash", "jwt", "token", "secret", "content"):
                    safe_metadata[k] = v

        audit_entry = AuditLog(
            actor_id=actor_id,
            job_id=job_id,
            action=action,
            ip_address=ip_address,
            meta_data=safe_metadata if safe_metadata else None
        )
        db.add(audit_entry)
        db.flush()
        return audit_entry

    log = log_event


audit_service = AuditService()
