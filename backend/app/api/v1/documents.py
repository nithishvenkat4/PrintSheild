from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.document import (
    DocumentUploadUrlRequest,
    DocumentUploadUrlResponse,
    DocumentCompleteResponse
)
from app.services.document_service import document_service

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload-url", response_model=DocumentUploadUrlResponse, status_code=status.HTTP_200_OK)
def create_upload_url(
    request_data: DocumentUploadUrlRequest,
    req: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    client_ip = req.client.host if req.client else None
    data = document_service.create_upload_url(
        db=db,
        current_user=current_user,
        request=request_data,
        ip_address=client_ip
    )
    return DocumentUploadUrlResponse(data=data)


@router.post("/{document_id}/complete", response_model=DocumentCompleteResponse, status_code=status.HTTP_200_OK)
def complete_upload(
    document_id: str,
    req: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    client_ip = req.client.host if req.client else None
    data = document_service.complete_upload(
        db=db,
        current_user=current_user,
        document_id=document_id,
        ip_address=client_ip
    )
    return DocumentCompleteResponse(data=data)
