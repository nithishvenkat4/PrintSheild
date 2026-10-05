from typing import Optional
from fastapi import APIRouter, Depends, Request, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_active_user, require_shop_owner
from app.models.user import User
from app.schemas.job import (
    JobCreateRequest,
    JobCreateResponse,
    JobDetailResponse,
    CustomerJobListResponse,
    CustomerJobsData,
    JobCancelResponse,
    ShopQueueResponse,
    ShopQueueData,
    JobStartResponse,
    DocumentAccessResponse,
    JobCompleteResponse,
    JobFailRequest,
    JobFailResponse
)
from app.services.job_service import job_service

# Customer jobs router: mounted at /jobs
customer_jobs_router = APIRouter(prefix="/jobs", tags=["Customer Jobs"])

# Shop jobs router: mounted at /shop/jobs
shop_jobs_router = APIRouter(prefix="/shop/jobs", tags=["Shop Jobs"])


# ============================================================================
# Customer Job Endpoints
# ============================================================================

@customer_jobs_router.post("", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    request_data: JobCreateRequest,
    req: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    client_ip = req.client.host if req.client else None
    job_detail = job_service.create_job(
        db=db,
        current_user=current_user,
        request=request_data,
        ip_address=client_ip
    )
    return JobCreateResponse(data=job_detail)


@customer_jobs_router.get("", response_model=CustomerJobListResponse, status_code=status.HTTP_200_OK)
def get_customer_jobs(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    cursor: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    jobs = job_service.get_customer_jobs(
        db=db,
        current_user=current_user,
        status=status,
        limit=limit,
        cursor=cursor
    )
    return CustomerJobListResponse(data=CustomerJobsData(jobs=jobs))


@customer_jobs_router.get("/{job_id}", response_model=JobDetailResponse, status_code=status.HTTP_200_OK)
def get_job_detail(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    detail = job_service.get_job_detail(
        db=db,
        current_user=current_user,
        job_id=job_id
    )
    return JobDetailResponse(data=detail)


@customer_jobs_router.post("/{job_id}/cancel", response_model=JobCancelResponse, status_code=status.HTTP_200_OK)
def cancel_job(
    job_id: str,
    req: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    client_ip = req.client.host if req.client else None
    cancel_data = job_service.cancel_job(
        db=db,
        current_user=current_user,
        job_id=job_id,
        ip_address=client_ip
    )
    return JobCancelResponse(data=cancel_data)


# ============================================================================
# Shop Job Endpoints
# ============================================================================

@shop_jobs_router.get("", response_model=ShopQueueResponse, status_code=status.HTTP_200_OK)
def get_shop_queue(
    status: Optional[str] = Query("WAITING"),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(require_shop_owner),
    db: Session = Depends(get_db)
):
    queue_items = job_service.get_shop_queue(
        db=db,
        current_user=current_user,
        status=status,
        limit=limit
    )
    return ShopQueueResponse(data=ShopQueueData(jobs=queue_items))


@shop_jobs_router.post("/{job_id}/start", response_model=JobStartResponse, status_code=status.HTTP_200_OK)
def start_job(
    job_id: str,
    req: Request,
    current_user: User = Depends(require_shop_owner),
    db: Session = Depends(get_db)
):
    client_ip = req.client.host if req.client else None
    start_data = job_service.start_job(
        db=db,
        current_user=current_user,
        job_id=job_id,
        ip_address=client_ip
    )
    return JobStartResponse(data=start_data)


@shop_jobs_router.post("/{job_id}/document-access", response_model=DocumentAccessResponse, status_code=status.HTTP_200_OK)
def get_document_access(
    job_id: str,
    req: Request,
    current_user: User = Depends(require_shop_owner),
    db: Session = Depends(get_db)
):
    client_ip = req.client.host if req.client else None
    access_data = job_service.get_document_access(
        db=db,
        current_user=current_user,
        job_id=job_id,
        ip_address=client_ip
    )
    return DocumentAccessResponse(data=access_data)


@shop_jobs_router.post("/{job_id}/complete", response_model=JobCompleteResponse, status_code=status.HTTP_200_OK)
def complete_job(
    job_id: str,
    req: Request,
    current_user: User = Depends(require_shop_owner),
    db: Session = Depends(get_db)
):
    client_ip = req.client.host if req.client else None
    complete_data = job_service.complete_job(
        db=db,
        current_user=current_user,
        job_id=job_id,
        ip_address=client_ip
    )
    return JobCompleteResponse(data=complete_data)


@shop_jobs_router.post("/{job_id}/fail", response_model=JobFailResponse, status_code=status.HTTP_200_OK)
def fail_job(
    job_id: str,
    request_data: JobFailRequest,
    req: Request,
    current_user: User = Depends(require_shop_owner),
    db: Session = Depends(get_db)
):
    client_ip = req.client.host if req.client else None
    fail_data = job_service.fail_job(
        db=db,
        current_user=current_user,
        job_id=job_id,
        request=request_data,
        ip_address=client_ip
    )
    return JobFailResponse(data=fail_data)
