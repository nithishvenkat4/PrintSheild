import uuid
from typing import Optional
from pydantic import BaseModel, Field


class DocumentUploadUrlRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    mime_type: str = Field(..., min_length=3, max_length=100)
    file_size: int = Field(..., gt=0)


class DocumentUploadUrlData(BaseModel):
    document_id: uuid.UUID
    upload_url: str
    expires_in: int = 300


class DocumentUploadUrlResponse(BaseModel):
    data: DocumentUploadUrlData


class DocumentCompleteRequest(BaseModel):
    pass


class DocumentCompleteData(BaseModel):
    document_id: uuid.UUID
    status: str = "AVAILABLE"
    filename: str
    size: int


class DocumentCompleteResponse(BaseModel):
    data: DocumentCompleteData
