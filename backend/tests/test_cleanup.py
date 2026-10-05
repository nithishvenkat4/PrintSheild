import uuid
import pytest
from datetime import datetime, timezone, timedelta
from app.models.document import Document
from app.models.print_job import PrintJob, PrintJobStatus
from app.workers.cleanup import run_cleanup_cycle


def test_cleanup_cycle_expires_jobs(db, customer_user, registered_shop):
    # Expired document and job in the past
    past_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    doc = Document(
        id=uuid.uuid4(),
        owner_id=customer_user.id,
        original_filename="expired_doc.pdf",
        storage_key=f"jobs/{uuid.uuid4()}/expired.pdf",
        mime_type="application/pdf",
        file_size=12000,
        checksum_sha256="0" * 64,
        expires_at=past_time
    )
    db.add(doc)
    db.commit()

    job = PrintJob(
        id=uuid.uuid4(),
        customer_id=customer_user.id,
        shop_id=registered_shop.id,
        document_id=doc.id,
        copy_count=1,
        status=PrintJobStatus.WAITING,
        pickup_code="9999",
        expires_at=past_time
    )
    doc.job_id = job.id
    db.add(job)
    db.commit()

    # Run cleanup
    result = run_cleanup_cycle(db)

    assert result["expired_jobs"] >= 1
    assert result["cleaned_documents"] >= 1

    # Verify job status changed to EXPIRED
    db.refresh(job)
    assert job.status == PrintJobStatus.EXPIRED

    # Verify document deleted_at set
    db.refresh(doc)
    assert doc.deleted_at is not None


def test_cleanup_cycle_orphan_documents(db, customer_user):
    past_time = datetime.now(timezone.utc) - timedelta(minutes=15)

    orphan_doc = Document(
        id=uuid.uuid4(),
        owner_id=customer_user.id,
        original_filename="abandoned.pdf",
        storage_key=f"jobs/{uuid.uuid4()}/abandoned.pdf",
        mime_type="application/pdf",
        file_size=5000,
        checksum_sha256="0" * 64,
        expires_at=past_time
    )
    db.add(orphan_doc)
    db.commit()

    result = run_cleanup_cycle(db)
    assert result["cleaned_documents"] >= 1

    db.refresh(orphan_doc)
    assert orphan_doc.deleted_at is not None
