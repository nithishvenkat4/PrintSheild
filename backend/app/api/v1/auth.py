from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_active_user
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    RegisterResponse,
    RegisterResponseData,
    LoginRequest,
    LoginResponse,
    LoginResponseData,
    CurrentUserResponse,
    UserResponse
)
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=RegisterResponse, status_code=status.HTTP_201_CREATED)
def register(
    request_data: RegisterRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    client_ip = req.client.host if req.client else None
    user = auth_service.register(
        db=db,
        name=request_data.name,
        email=request_data.email,
        password=request_data.password,
        role=request_data.role,
        ip_address=client_ip
    )
    return RegisterResponse(
        data=RegisterResponseData(
            user=UserResponse.model_validate(user)
        )
    )


@router.post("/login", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def login(
    request_data: LoginRequest,
    req: Request,
    db: Session = Depends(get_db)
):
    client_ip = req.client.host if req.client else None
    res = auth_service.login(
        db=db,
        email=request_data.email,
        password=request_data.password,
        ip_address=client_ip
    )
    return LoginResponse(
        data=LoginResponseData(
            access_token=res["access_token"],
            token_type=res["token_type"],
            user=UserResponse.model_validate(res["user"])
        )
    )


@router.get("/me", response_model=CurrentUserResponse, status_code=status.HTTP_200_OK)
def get_me(
    current_user: User = Depends(get_current_active_user)
):
    return CurrentUserResponse(
        data=UserResponse.model_validate(current_user)
    )
