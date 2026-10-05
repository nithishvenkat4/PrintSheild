from typing import Any, Optional
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorCode:
    # Auth
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
    AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
    AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
    AUTH_INSUFFICIENT_ROLE = "AUTH_INSUFFICIENT_ROLE"

    # Shop
    SHOP_NOT_FOUND = "SHOP_NOT_FOUND"
    SHOP_INACTIVE = "SHOP_INACTIVE"
    SHOP_NOT_OWNER = "SHOP_NOT_OWNER"

    # Document
    DOCUMENT_NOT_FOUND = "DOCUMENT_NOT_FOUND"
    DOCUMENT_NOT_READY = "DOCUMENT_NOT_READY"
    DOCUMENT_EXPIRED = "DOCUMENT_EXPIRED"
    DOCUMENT_ACCESS_DENIED = "DOCUMENT_ACCESS_DENIED"
    DOCUMENT_INVALID_TYPE = "DOCUMENT_INVALID_TYPE"
    DOCUMENT_TOO_LARGE = "DOCUMENT_TOO_LARGE"

    # Job
    JOB_NOT_FOUND = "JOB_NOT_FOUND"
    JOB_ACCESS_DENIED = "JOB_ACCESS_DENIED"
    JOB_INVALID_STATE = "JOB_INVALID_STATE"
    JOB_EXPIRED = "JOB_EXPIRED"
    JOB_ALREADY_PRINTING = "JOB_ALREADY_PRINTING"
    JOB_CANNOT_CANCEL = "JOB_CANNOT_CANCEL"
    INVALID_COPY_COUNT = "INVALID_COPY_COUNT"

    # Location
    INVALID_LOCATION = "INVALID_LOCATION"

    # QR
    INVALID_QR = "INVALID_QR"
    QR_SHOP_NOT_FOUND = "QR_SHOP_NOT_FOUND"

    # Platform
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class AppException(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message
            }
        }
    )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return error_response(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    first_error = exc.errors()[0] if exc.errors() else {}
    msg = first_error.get("msg", "Validation error")
    loc = " -> ".join(str(l) for l in first_error.get("loc", []))
    detail = f"{loc}: {msg}" if loc else msg
    return error_response(
        status_code=422,
        code=ErrorCode.INTERNAL_ERROR,
        message=detail
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = ErrorCode.INTERNAL_ERROR
    if exc.status_code == 401:
        code = ErrorCode.AUTH_TOKEN_INVALID
    elif exc.status_code == 403:
        code = ErrorCode.AUTH_INSUFFICIENT_ROLE
    elif exc.status_code == 404:
        code = ErrorCode.INTERNAL_ERROR
    elif exc.status_code == 429:
        code = ErrorCode.RATE_LIMITED

    return error_response(
        status_code=exc.status_code,
        code=code,
        message=str(exc.detail)
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response(
        status_code=500,
        code=ErrorCode.INTERNAL_ERROR,
        message="An internal server error occurred."
    )
