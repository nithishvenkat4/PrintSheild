import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from app.models.print_job import PrintJobStatus


class JobShopBrief(BaseModel):
    id: uuid.UUID
    name: str


class JobDocumentBrief(BaseModel):
    id: uuid.UUID
    filename: str


class JobCreateRequest(BaseModel):
    shop_id: uuid.UUID
    document_id: uuid.UUID
    copy_count: int = Field(..., ge=1, le=20)


class JobDetail(BaseModel):
    id: uuid.UUID
    shop: JobShopBrief
    document: JobDocumentBrief
    copy_count: int
    status: PrintJobStatus
    pickup_code: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    expires_at: datetime
    failure_reason: Optional[str] = None


class JobCreateResponse(BaseModel):
    data: JobDetail


class JobDetailResponse(BaseModel):
    data: JobDetail


class CustomerJobsData(BaseModel):
    jobs: List[JobDetail]


class CustomerJobListResponse(BaseModel):
    data: CustomerJobsData


class JobCancelData(BaseModel):
    id: uuid.UUID
    status: PrintJobStatus = PrintJobStatus.CANCELLED


class JobCancelResponse(BaseModel):
    data: JobCancelData


class ShopQueueItem(BaseModel):
    id: uuid.UUID
    pickup_code: str
    copy_count: int
    filename: str
    status: PrintJobStatus
    created_at: datetime


class ShopQueueData(BaseModel):
    jobs: List[ShopQueueItem]


class ShopQueueResponse(BaseModel):
    data: ShopQueueData


class JobStartData(BaseModel):
    id: uuid.UUID
    status: PrintJobStatus = PrintJobStatus.PRINTING
    started_at: datetime


class JobStartResponse(BaseModel):
    data: JobStartData


class DocumentAccessData(BaseModel):
    download_url: str
    expires_in: int = 120


class DocumentAccessResponse(BaseModel):
    data: DocumentAccessData


class JobCompleteData(BaseModel):
    id: uuid.UUID
    status: PrintJobStatus = PrintJobStatus.COMPLETED
    completed_at: datetime


class JobCompleteResponse(BaseModel):
    data: JobCompleteData


class JobFailRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


class JobFailData(BaseModel):
    id: uuid.UUID
    status: PrintJobStatus = PrintJobStatus.FAILED
    failure_reason: str


class JobFailResponse(BaseModel):
    data: JobFailData
