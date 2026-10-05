import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.models.user import UserRole


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., min_length=6, max_length=128)
    role: Optional[UserRole] = Field(default=UserRole.CUSTOMER)


class UserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    role: UserRole

    model_config = {"from_attributes": True}


class RegisterResponseData(BaseModel):
    user: UserResponse


class RegisterResponse(BaseModel):
    data: RegisterResponseData


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponseData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class LoginResponse(BaseModel):
    data: LoginResponseData


class CurrentUserResponse(BaseModel):
    data: UserResponse
