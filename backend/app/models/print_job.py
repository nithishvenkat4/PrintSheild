import enum
import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, SmallInteger, Text, ForeignKey, Uuid, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UTCDatetime


class PrintJobStatus(str, enum.Enum):
    CREATED = "CREATED"
    WAITING = "WAITING"
    PRINTING = "PRINTING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class PrintJob(Base):
    __tablename__ = "print_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    customer_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    shop_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("shops.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )
    copy_count: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[PrintJobStatus] = mapped_column(
        Enum(PrintJobStatus, name="print_job_status", native_enum=True),
        nullable=False,
        default=PrintJobStatus.WAITING
    )
    pickup_code: Mapped[str] = mapped_column(String(6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDatetime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(UTCDatetime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(UTCDatetime, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(UTCDatetime, nullable=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        UTCDatetime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    customer = relationship("User", back_populates="print_jobs")
    shop = relationship("Shop", back_populates="print_jobs")
    document = relationship("Document", foreign_keys=[document_id], back_populates="print_job")
    audit_logs = relationship("AuditLog", back_populates="job")

    __table_args__ = (
        Index("idx_print_jobs_customer", "customer_id"),
        Index("idx_print_jobs_shop_status", "shop_id", "status"),
        Index("idx_print_jobs_expires", "expires_at"),
    )
