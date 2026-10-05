import os
import uuid
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AppException, ErrorCode
from app.models.user import User, UserRole
from app.models.document import Document
from app.models.audit_log import AuditAction
from app.schemas.document import (
    DocumentUploadUrlRequest,
    DocumentUploadUrlData,
    DocumentCompleteData
)
from app.services.s3_service import s3_service
from app.services.audit_service import audit_service


ALLOWED_EXTENSIONS = {".pdf", ".jpeg", ".jpg", ".png"}
ALLOWED_MIME_TYPES = {"application/pdf", "image/jpeg", "image/jpg", "image/png"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


class DocumentService:
    @staticmethod
    def create_upload_url(
        db: Session,
        current_user: User,
        request: DocumentUploadUrlRequest,
        ip_address: str | None = None
    ) -> DocumentUploadUrlData:
        # Validate size
        if request.file_size > MAX_FILE_SIZE:
            raise AppException(
                status_code=400,
                code=ErrorCode.DOCUMENT_TOO_LARGE,
                message="File size exceeds the maximum limit of 20MB."
            )

        # Validate file extension
        _, ext = os.path.splitext(request.filename.lower())
        if ext not in ALLOWED_EXTENSIONS or request.mime_type.lower() not in ALLOWED_MIME_TYPES:
            raise AppException(
                status_code=400,
                code=ErrorCode.DOCUMENT_INVALID_TYPE,
                message="Invalid file type. Only PDF, JPEG, and PNG files are allowed."
            )

        document_id = uuid.uuid4()
        storage_key = f"jobs/{document_id}/{secrets.token_hex(8)}{ext}"
        expires_in = 300  # 5 minutes for upload
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.DOCUMENT_EXPIRY_MINUTES)

        upload_url = s3_service.generate_presigned_upload_url(
            storage_key=storage_key,
            mime_type=request.mime_type,
            expires_in=expires_in
        )

        checksum = hashlib.sha256(str(document_id).encode()).hexdigest()

        document = Document(
            id=document_id,
            owner_id=current_user.id,
            original_filename=request.filename,
            storage_key=storage_key,
            mime_type=request.mime_type,
            file_size=request.file_size,
            checksum_sha256=checksum,
            expires_at=expires_at
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        audit_service.log(
            db=db,
            action=AuditAction.DOCUMENT_UPLOADED,
            actor_id=current_user.id,
            ip_address=ip_address,
            metadata={
                "document_id": str(document.id),
                "filename": document.original_filename,
                "file_size": document.file_size
            }
        )

        return DocumentUploadUrlData(
            document_id=document.id,
            upload_url=upload_url,
            expires_in=expires_in
        )

    @staticmethod
    def complete_upload(
        db: Session,
        current_user: User,
        document_id: str | uuid.UUID,
        ip_address: str | None = None
    ) -> DocumentCompleteData:
        if isinstance(document_id, str):
            try:
                document_id = uuid.UUID(document_id)
            except ValueError:
                raise AppException(
                    status_code=404,
                    code=ErrorCode.DOCUMENT_NOT_FOUND,
                    message="Document not found."
                )

        document = db.query(Document).filter(
            Document.id == document_id,
            Document.deleted_at.is_(None)
        ).first()

        if not document:
            raise AppException(
                status_code=404,
                code=ErrorCode.DOCUMENT_NOT_FOUND,
                message="Document not found."
            )

        if document.owner_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise AppException(
                status_code=403,
                code=ErrorCode.DOCUMENT_ACCESS_DENIED,
                message="Access denied to this document."
            )

        doc_expires_at = (
            document.expires_at
            if document.expires_at.tzinfo
            else document.expires_at.replace(tzinfo=timezone.utc)
        )
        if doc_expires_at < datetime.now(timezone.utc):
            raise AppException(
                status_code=400,
                code=ErrorCode.DOCUMENT_EXPIRED,
                message="Document has expired."
            )

        if not s3_service.check_object_exists(document.storage_key):
            raise AppException(
                status_code=400,
                code=ErrorCode.DOCUMENT_NOT_READY,
                message="Document has not been uploaded to storage yet."
            )

        return DocumentCompleteData(
            document_id=document.id,
            status="AVAILABLE",
            filename=document.original_filename,
            size=document.file_size
        )


document_service = DocumentService()
