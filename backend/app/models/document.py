import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import String, Text, BigInteger, CHAR, ForeignKey, Uuid, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UTCDatetime


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    job_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid,
        ForeignKey("print_jobs.id", ondelete="SET NULL", use_alter=True, name="fk_documents_job_id"),
        unique=True,
        nullable=True
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        UTCDatetime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(UTCDatetime, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(UTCDatetime, nullable=True)

    # Relationships
    owner = relationship("User", back_populates="documents")
    print_job = relationship("PrintJob", foreign_keys="PrintJob.document_id", back_populates="document", uselist=False)

    __table_args__ = (
        Index("idx_documents_owner", "owner_id"),
    )
