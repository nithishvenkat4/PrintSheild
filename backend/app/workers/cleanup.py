import logging
from datetime import datetime, timezone
from typing import Dict, Any
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.print_job import PrintJob, PrintJobStatus
from app.models.document import Document
from app.models.audit_log import AuditAction
from app.services.s3_service import s3_service
from app.services.audit_service import audit_service

logger = logging.getLogger(__name__)


def run_cleanup_cycle(db: Session) -> Dict[str, Any]:
    """
    Run one cycle of expired job and document cleanup.
    1. Finds WAITING or CREATED jobs where expires_at < now.
    2. Marks them EXPIRED and triggers document deletion.
    3. Finds orphan documents where expires_at < now and deleted_at is None.
    4. Deletes their S3 objects and marks deleted_at.
    """
    now = datetime.now(timezone.utc)
    expired_jobs_count = 0
    cleaned_documents_count = 0

    try:
        # 1. Cleanup expired jobs
        expired_jobs = db.query(PrintJob).filter(
            PrintJob.status.in_([PrintJobStatus.WAITING, PrintJobStatus.CREATED]),
            PrintJob.expires_at < now
        ).all()

        for job in expired_jobs:
            job.status = PrintJobStatus.EXPIRED
            job.updated_at = now
            expired_jobs_count += 1

            audit_service.log(
                db=db,
                action=AuditAction.JOB_EXPIRED,
                job_id=job.id,
                metadata={"expired_at": now.isoformat()}
            )

            # Cleanup document
            document = db.query(Document).filter(
                Document.id == job.document_id,
                Document.deleted_at.is_(None)
            ).first()

            if document:
                document.deleted_at = now
                s3_service.delete_object(document.storage_key)
                cleaned_documents_count += 1
                audit_service.log(
                    db=db,
                    action=AuditAction.DOCUMENT_DELETED,
                    job_id=job.id,
                    metadata={"document_id": str(document.id), "reason": "job_expired"}
                )

        # 2. Cleanup orphan expired documents
        orphan_docs = db.query(Document).filter(
            Document.deleted_at.is_(None),
            Document.expires_at < now
        ).all()

        for doc in orphan_docs:
            doc.deleted_at = now
            s3_service.delete_object(doc.storage_key)
            cleaned_documents_count += 1
            audit_service.log(
                db=db,
                action=AuditAction.DOCUMENT_DELETED,
                metadata={"document_id": str(doc.id), "reason": "document_expired"}
            )

        db.commit()
        logger.info(
            f"Cleanup cycle completed: {expired_jobs_count} jobs expired, "
            f"{cleaned_documents_count} documents cleaned up."
        )
    except Exception as e:
        db.rollback()
        logger.error(f"Error during cleanup cycle: {e}")
        raise

    return {
        "expired_jobs": expired_jobs_count,
        "cleaned_documents": cleaned_documents_count
    }


def run_worker_once():
    """Entry point for running cleanup once in CLI or cron."""
    db = SessionLocal()
    try:
        return run_cleanup_cycle(db)
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting PrintShield cleanup worker...")
    result = run_worker_once()
    logger.info(f"Worker finished. Result: {result}")
