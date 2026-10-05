import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.exceptions import AppException, ErrorCode
from app.models.user import User, UserRole
from app.models.shop import Shop
from app.models.document import Document
from app.models.print_job import PrintJob, PrintJobStatus
from app.models.audit_log import AuditAction
from app.schemas.job import (
    JobCreateRequest,
    JobDetail,
    JobShopBrief,
    JobDocumentBrief,
    JobCancelData,
    ShopQueueItem,
    JobStartData,
    DocumentAccessData,
    JobCompleteData,
    JobFailRequest,
    JobFailData
)
from app.services.s3_service import s3_service
from app.services.audit_service import audit_service


class JobService:
    @staticmethod
    def _build_job_detail(job: PrintJob) -> JobDetail:
        return JobDetail(
            id=job.id,
            shop=JobShopBrief(id=job.shop.id, name=job.shop.name),
            document=JobDocumentBrief(id=job.document.id, filename=job.document.original_filename),
            copy_count=job.copy_count,
            status=job.status,
            pickup_code=job.pickup_code,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            expires_at=job.expires_at,
            failure_reason=job.failure_reason
        )

    @staticmethod
    def create_job(
        db: Session,
        current_user: User,
        request: JobCreateRequest,
        ip_address: Optional[str] = None
    ) -> JobDetail:
        if request.copy_count < 1 or request.copy_count > 20:
            raise AppException(
                status_code=400,
                code=ErrorCode.INVALID_COPY_COUNT,
                message="Copy count must be between 1 and 20."
            )

        shop_id = request.shop_id if isinstance(request.shop_id, uuid.UUID) else uuid.UUID(str(request.shop_id))
        shop = db.query(Shop).filter(Shop.id == shop_id).first()
        if not shop:
            raise AppException(
                status_code=404,
                code=ErrorCode.SHOP_NOT_FOUND,
                message="Shop not found."
            )
        if not shop.is_open:
            raise AppException(
                status_code=400,
                code=ErrorCode.SHOP_INACTIVE,
                message="Shop is currently inactive."
            )

        doc_id = request.document_id if isinstance(request.document_id, uuid.UUID) else uuid.UUID(str(request.document_id))
        document = db.query(Document).filter(
            Document.id == doc_id,
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

        if document.job_id is not None:
            raise AppException(
                status_code=400,
                code=ErrorCode.JOB_INVALID_STATE,
                message="A print job has already been created for this document."
            )

        pickup_code = f"{secrets.randbelow(9000) + 1000}"
        job_id = uuid.uuid4()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.JOB_EXPIRY_MINUTES)

        job = PrintJob(
            id=job_id,
            customer_id=current_user.id,
            shop_id=shop.id,
            document_id=document.id,
            copy_count=request.copy_count,
            status=PrintJobStatus.WAITING,
            pickup_code=pickup_code,
            expires_at=expires_at
        )

        document.job_id = job.id
        db.add(job)
        db.commit()

        # Re-fetch with relationships loaded
        job = db.query(PrintJob).options(
            joinedload(PrintJob.shop),
            joinedload(PrintJob.document)
        ).filter(PrintJob.id == job_id).first()

        audit_service.log(
            db=db,
            action=AuditAction.JOB_CREATED,
            actor_id=current_user.id,
            job_id=job.id,
            ip_address=ip_address,
            metadata={
                "shop_id": str(shop.id),
                "document_id": str(document.id),
                "copy_count": job.copy_count,
                "pickup_code": job.pickup_code
            }
        )

        return JobService._build_job_detail(job)

    @staticmethod
    def get_customer_jobs(
        db: Session,
        current_user: User,
        status: Optional[str] = None,
        limit: int = 50,
        cursor: Optional[str] = None
    ) -> List[JobDetail]:
        query = db.query(PrintJob).options(
            joinedload(PrintJob.shop),
            joinedload(PrintJob.document)
        ).filter(PrintJob.customer_id == current_user.id)

        if status:
            try:
                status_enum = PrintJobStatus(status.upper())
                query = query.filter(PrintJob.status == status_enum)
            except ValueError:
                pass

        jobs = query.order_by(PrintJob.created_at.desc()).limit(limit).all()
        return [JobService._build_job_detail(j) for j in jobs]

    @staticmethod
    def get_job_detail(
        db: Session,
        current_user: User,
        job_id: str | uuid.UUID
    ) -> JobDetail:
        if isinstance(job_id, str):
            try:
                job_id = uuid.UUID(job_id)
            except ValueError:
                raise AppException(
                    status_code=404,
                    code=ErrorCode.JOB_NOT_FOUND,
                    message="Print job not found."
                )

        job = db.query(PrintJob).options(
            joinedload(PrintJob.shop),
            joinedload(PrintJob.document)
        ).filter(PrintJob.id == job_id).first()

        if not job:
            raise AppException(
                status_code=404,
                code=ErrorCode.JOB_NOT_FOUND,
                message="Print job not found."
            )

        # Authorization: Customer owner, Shop owner, or Admin
        is_customer_owner = job.customer_id == current_user.id
        is_admin = current_user.role == UserRole.ADMIN
        is_shop_owner = False

        if current_user.role == UserRole.SHOP_OWNER:
            shop = db.query(Shop).filter(Shop.id == job.shop_id).first()
            if shop and shop.owner_id == current_user.id:
                is_shop_owner = True

        if not (is_customer_owner or is_shop_owner or is_admin):
            raise AppException(
                status_code=403,
                code=ErrorCode.JOB_ACCESS_DENIED,
                message="Access denied to this print job."
            )

        return JobService._build_job_detail(job)

    @staticmethod
    def cancel_job(
        db: Session,
        current_user: User,
        job_id: str | uuid.UUID,
        ip_address: Optional[str] = None
    ) -> JobCancelData:
        if isinstance(job_id, str):
            try:
                job_id = uuid.UUID(job_id)
            except ValueError:
                raise AppException(
                    status_code=404,
                    code=ErrorCode.JOB_NOT_FOUND,
                    message="Print job not found."
                )

        job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise AppException(
                status_code=404,
                code=ErrorCode.JOB_NOT_FOUND,
                message="Print job not found."
            )

        if job.customer_id != current_user.id and current_user.role != UserRole.ADMIN:
            raise AppException(
                status_code=403,
                code=ErrorCode.JOB_ACCESS_DENIED,
                message="Access denied to this print job."
            )

        if job.status == PrintJobStatus.PRINTING:
            raise AppException(
                status_code=409,
                code=ErrorCode.JOB_CANNOT_CANCEL,
                message="Cannot cancel a print job that is currently printing."
            )

        if job.status != PrintJobStatus.WAITING:
            raise AppException(
                status_code=409,
                code=ErrorCode.JOB_INVALID_STATE,
                message=f"Cannot cancel print job in {job.status.value} state."
            )

        now = datetime.now(timezone.utc)
        rows_updated = db.query(PrintJob).filter(
            PrintJob.id == job.id,
            PrintJob.status == PrintJobStatus.WAITING
        ).update(
            {"status": PrintJobStatus.CANCELLED, "updated_at": now},
            synchronize_session="fetch"
        )

        if rows_updated == 0:
            raise AppException(
                status_code=409,
                code=ErrorCode.JOB_CANNOT_CANCEL,
                message="Could not cancel job, status has changed."
            )

        # Clean up associated document
        document = db.query(Document).filter(Document.id == job.document_id).first()
        if document and document.deleted_at is None:
            document.deleted_at = now
            s3_service.delete_object(document.storage_key)
            audit_service.log(
                db=db,
                action=AuditAction.DOCUMENT_DELETED,
                actor_id=current_user.id,
                job_id=job.id,
                ip_address=ip_address,
                metadata={"document_id": str(document.id), "reason": "job_cancelled"}
            )

        audit_service.log(
            db=db,
            action=AuditAction.JOB_CANCELLED,
            actor_id=current_user.id,
            job_id=job.id,
            ip_address=ip_address
        )

        db.commit()
        return JobCancelData(id=job.id, status=PrintJobStatus.CANCELLED)

    @staticmethod
    def get_shop_queue(
        db: Session,
        current_user: User,
        status: Optional[str] = "WAITING",
        limit: int = 50
    ) -> List[ShopQueueItem]:
        shop = db.query(Shop).filter(Shop.owner_id == current_user.id).first()
        if not shop:
            raise AppException(
                status_code=404,
                code=ErrorCode.SHOP_NOT_FOUND,
                message="No shop found for current user."
            )

        query = db.query(PrintJob).options(
            joinedload(PrintJob.document)
        ).filter(PrintJob.shop_id == shop.id)

        if status:
            try:
                status_enum = PrintJobStatus(status.upper())
                query = query.filter(PrintJob.status == status_enum)
            except ValueError:
                pass

        # Queue order: FIFO (created_at ASC)
        jobs = query.order_by(PrintJob.created_at.asc()).limit(limit).all()

        return [
            ShopQueueItem(
                id=j.id,
                pickup_code=j.pickup_code,
                copy_count=j.copy_count,
                filename=j.document.original_filename if j.document else "unknown",
                status=j.status,
                created_at=j.created_at
            )
            for j in jobs
        ]

    @staticmethod
    def start_job(
        db: Session,
        current_user: User,
        job_id: str | uuid.UUID,
        ip_address: Optional[str] = None
    ) -> JobStartData:
        shop = db.query(Shop).filter(Shop.owner_id == current_user.id).first()
        if not shop:
            raise AppException(
                status_code=403,
                code=ErrorCode.SHOP_NOT_OWNER,
                message="You do not own a shop."
            )

        if isinstance(job_id, str):
            try:
                job_id = uuid.UUID(job_id)
            except ValueError:
                raise AppException(
                    status_code=404,
                    code=ErrorCode.JOB_NOT_FOUND,
                    message="Print job not found."
                )

        job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise AppException(
                status_code=404,
                code=ErrorCode.JOB_NOT_FOUND,
                message="Print job not found."
            )

        if job.shop_id != shop.id:
            raise AppException(
                status_code=403,
                code=ErrorCode.JOB_ACCESS_DENIED,
                message="This job does not belong to your shop."
            )

        job_expires_at = (
            job.expires_at
            if job.expires_at.tzinfo
            else job.expires_at.replace(tzinfo=timezone.utc)
        )
        if job_expires_at < datetime.now(timezone.utc):
            raise AppException(
                status_code=400,
                code=ErrorCode.JOB_EXPIRED,
                message="This print job has expired."
            )

        if job.status == PrintJobStatus.PRINTING:
            raise AppException(
                status_code=409,
                code=ErrorCode.JOB_ALREADY_PRINTING,
                message="Job is already printing."
            )

        if job.status not in (PrintJobStatus.WAITING, PrintJobStatus.FAILED):
            raise AppException(
                status_code=409,
                code=ErrorCode.JOB_INVALID_STATE,
                message=f"Cannot start job in state {job.status.value}."
            )

        now = datetime.now(timezone.utc)
        rows_updated = db.query(PrintJob).filter(
            PrintJob.id == job.id,
            PrintJob.status.in_([PrintJobStatus.WAITING, PrintJobStatus.FAILED])
        ).update(
            {"status": PrintJobStatus.PRINTING, "started_at": now, "updated_at": now},
            synchronize_session="fetch"
        )

        if rows_updated == 0:
            raise AppException(
                status_code=409,
                code=ErrorCode.JOB_ALREADY_PRINTING,
                message="Job is already printing or status changed."
            )

        db.commit()
        db.refresh(job)

        audit_service.log(
            db=db,
            action=AuditAction.JOB_STARTED,
            actor_id=current_user.id,
            job_id=job.id,
            ip_address=ip_address
        )

        return JobStartData(
            id=job.id,
            status=job.status,
            started_at=job.started_at
        )

    @staticmethod
    def get_document_access(
        db: Session,
        current_user: User,
        job_id: str | uuid.UUID,
        ip_address: Optional[str] = None
    ) -> DocumentAccessData:
        shop = db.query(Shop).filter(Shop.owner_id == current_user.id).first()
        if not shop:
            raise AppException(
                status_code=403,
                code=ErrorCode.SHOP_NOT_OWNER,
                message="You do not own a shop."
            )

        if isinstance(job_id, str):
            try:
                job_id = uuid.UUID(job_id)
            except ValueError:
                raise AppException(
                    status_code=404,
                    code=ErrorCode.JOB_NOT_FOUND,
                    message="Print job not found."
                )

        job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise AppException(
                status_code=404,
                code=ErrorCode.JOB_NOT_FOUND,
                message="Print job not found."
            )

        if job.shop_id != shop.id:
            raise AppException(
                status_code=403,
                code=ErrorCode.JOB_ACCESS_DENIED,
                message="This job does not belong to your shop."
            )

        if job.status != PrintJobStatus.PRINTING:
            raise AppException(
                status_code=409,
                code=ErrorCode.JOB_INVALID_STATE,
                message="Document access is only allowed when job is in PRINTING state."
            )

        job_expires_at = (
            job.expires_at
            if job.expires_at.tzinfo
            else job.expires_at.replace(tzinfo=timezone.utc)
        )
        if job_expires_at < datetime.now(timezone.utc):
            raise AppException(
                status_code=400,
                code=ErrorCode.JOB_EXPIRED,
                message="This print job has expired."
            )

        document = db.query(Document).filter(
            Document.id == job.document_id,
            Document.deleted_at.is_(None)
        ).first()

        if not document:
            raise AppException(
                status_code=404,
                code=ErrorCode.DOCUMENT_NOT_FOUND,
                message="Document not found or already deleted."
            )

        download_url = s3_service.generate_presigned_download_url(
            storage_key=document.storage_key,
            expires_in=120
        )

        return DocumentAccessData(
            download_url=download_url,
            expires_in=120
        )

    @staticmethod
    def complete_job(
        db: Session,
        current_user: User,
        job_id: str | uuid.UUID,
        ip_address: Optional[str] = None
    ) -> JobCompleteData:
        shop = db.query(Shop).filter(Shop.owner_id == current_user.id).first()
        if not shop:
            raise AppException(
                status_code=403,
                code=ErrorCode.SHOP_NOT_OWNER,
                message="You do not own a shop."
            )

        if isinstance(job_id, str):
            try:
                job_id = uuid.UUID(job_id)
            except ValueError:
                raise AppException(
                    status_code=404,
                    code=ErrorCode.JOB_NOT_FOUND,
                    message="Print job not found."
                )

        job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise AppException(
                status_code=404,
                code=ErrorCode.JOB_NOT_FOUND,
                message="Print job not found."
            )

        if job.shop_id != shop.id:
            raise AppException(
                status_code=403,
                code=ErrorCode.JOB_ACCESS_DENIED,
                message="This job does not belong to your shop."
            )

        if job.status != PrintJobStatus.PRINTING:
            raise AppException(
                status_code=409,
                code=ErrorCode.JOB_INVALID_STATE,
                message=f"Cannot complete job in {job.status.value} state. Must be PRINTING."
            )

        now = datetime.now(timezone.utc)
        rows_updated = db.query(PrintJob).filter(
            PrintJob.id == job.id,
            PrintJob.status == PrintJobStatus.PRINTING
        ).update(
            {"status": PrintJobStatus.COMPLETED, "completed_at": now, "updated_at": now},
            synchronize_session="fetch"
        )

        if rows_updated == 0:
            raise AppException(
                status_code=409,
                code=ErrorCode.JOB_INVALID_STATE,
                message="Job status has changed."
            )

        # Document cleanup: delete from S3 and record deleted_at
        document = db.query(Document).filter(Document.id == job.document_id).first()
        if document and document.deleted_at is None:
            document.deleted_at = now
            s3_service.delete_object(document.storage_key)
            audit_service.log(
                db=db,
                action=AuditAction.DOCUMENT_DELETED,
                actor_id=current_user.id,
                job_id=job.id,
                ip_address=ip_address,
                metadata={"document_id": str(document.id), "reason": "job_completed"}
            )

        audit_service.log(
            db=db,
            action=AuditAction.JOB_COMPLETED,
            actor_id=current_user.id,
            job_id=job.id,
            ip_address=ip_address
        )

        db.commit()
        db.refresh(job)

        return JobCompleteData(
            id=job.id,
            status=job.status,
            completed_at=job.completed_at
        )

    @staticmethod
    def fail_job(
        db: Session,
        current_user: User,
        job_id: str | uuid.UUID,
        request: JobFailRequest,
        ip_address: Optional[str] = None
    ) -> JobFailData:
        shop = db.query(Shop).filter(Shop.owner_id == current_user.id).first()
        if not shop:
            raise AppException(
                status_code=403,
                code=ErrorCode.SHOP_NOT_OWNER,
                message="You do not own a shop."
            )

        if isinstance(job_id, str):
            try:
                job_id = uuid.UUID(job_id)
            except ValueError:
                raise AppException(
                    status_code=404,
                    code=ErrorCode.JOB_NOT_FOUND,
                    message="Print job not found."
                )

        job = db.query(PrintJob).filter(PrintJob.id == job_id).first()
        if not job:
            raise AppException(
                status_code=404,
                code=ErrorCode.JOB_NOT_FOUND,
                message="Print job not found."
            )

        if job.shop_id != shop.id:
            raise AppException(
                status_code=403,
                code=ErrorCode.JOB_ACCESS_DENIED,
                message="This job does not belong to your shop."
            )

        if job.status != PrintJobStatus.PRINTING:
            raise AppException(
                status_code=409,
                code=ErrorCode.JOB_INVALID_STATE,
                message=f"Cannot fail job in {job.status.value} state. Must be PRINTING."
            )

        now = datetime.now(timezone.utc)
        rows_updated = db.query(PrintJob).filter(
            PrintJob.id == job.id,
            PrintJob.status == PrintJobStatus.PRINTING
        ).update(
            {"status": PrintJobStatus.FAILED, "failure_reason": request.reason, "updated_at": now},
            synchronize_session="fetch"
        )

        if rows_updated == 0:
            raise AppException(
                status_code=409,
                code=ErrorCode.JOB_INVALID_STATE,
                message="Job status has changed."
            )

        audit_service.log(
            db=db,
            action=AuditAction.JOB_FAILED,
            actor_id=current_user.id,
            job_id=job.id,
            ip_address=ip_address,
            metadata={"reason": request.reason}
        )

        db.commit()
        db.refresh(job)

        return JobFailData(
            id=job.id,
            status=job.status,
            failure_reason=job.failure_reason or request.reason
        )


job_service = JobService()
