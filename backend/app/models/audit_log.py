import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import String, ForeignKey, Uuid, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, IPAddressType, JSONBType, UTCDatetime


class AuditAction:
    USER_REGISTERED = "USER_REGISTERED"
    USER_LOGIN = "USER_LOGIN"
    SHOP_CREATED = "SHOP_CREATED"
    QR_ACCESSED = "QR_ACCESSED"
    DOCUMENT_UPLOADED = "DOCUMENT_UPLOADED"
    JOB_CREATED = "JOB_CREATED"
    JOB_CANCELLED = "JOB_CANCELLED"
    JOB_STARTED = "JOB_STARTED"
    JOB_COMPLETED = "JOB_COMPLETED"
    JOB_FAILED = "JOB_FAILED"
    JOB_EXPIRED = "JOB_EXPIRED"
    DOCUMENT_DELETED = "DOCUMENT_DELETED"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("print_jobs.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDatetime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    ip_address: Mapped[Optional[str]] = mapped_column(IPAddressType, nullable=True)
    meta_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        "metadata",
        JSONBType,
        nullable=True
    )

    # Relationships
    actor = relationship("User", back_populates="audit_logs")
    job = relationship("PrintJob", back_populates="audit_logs")

    __table_args__ = (
        Index("idx_audit_logs_job", "job_id"),
    )
