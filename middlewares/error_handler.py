"""
🔴 Global Exception Handler va Error Recovery
"""

import logging
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from jose import JWTError
from utils.admin_alerts import send_error_to_admins, format_details_for_alert

logger = logging.getLogger(__name__)


class ErrorResponse:
    """Standard error response format."""
    
    @staticmethod
    def build(
        status_code: int,
        message: str,
        error_code: str = None,
        details: dict = None,
        request_id: str = None
    ) -> dict:
        return {
            "status": "error",
            "status_code": status_code,
            "message": message,
            "error_code": error_code,
            "details": details or {},
            "request_id": request_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """🔴 Barcha exceptions uchun universal handler."""
    
    request_id = str(uuid.uuid4())
    method = request.method
    path = request.url.path
    client = request.client.host if request.client else "unknown"
    
    # ─────────────────────────────────────────────────────────────
    # DATABASE ERRORS
    # ─────────────────────────────────────────────────────────────
    if isinstance(exc, IntegrityError):
        # Duplicate entry, foreign key violation, etc.
        logger.warning(
            f"[{request_id}] Database Integrity Error",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "client": client,
                "error": str(exc.orig),
            }
        )
        await send_error_to_admins(
            title="Database Integrity Error",
            request_id=request_id,
            method=method,
            path=path,
            client=client,
            exc_type=type(exc).__name__,
            details=format_details_for_alert(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=ErrorResponse.build(
                status_code=409,
                message="Database conflict - duplicate entry or invalid reference",
                error_code="CONFLICT",
                request_id=request_id
            )
        )
    
    elif isinstance(exc, SQLAlchemyError):
        # General database errors (connection, syntax, etc.)
        logger.error(
            f"[{request_id}] Database Error",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "client": client,
            },
            exc_info=exc
        )
        await send_error_to_admins(
            title="Database Error",
            request_id=request_id,
            method=method,
            path=path,
            client=client,
            exc_type=type(exc).__name__,
            details=format_details_for_alert(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse.build(
                status_code=500,
                message="Database operation failed",
                error_code="DATABASE_ERROR",
                request_id=request_id
            )
        )
    
    # ─────────────────────────────────────────────────────────────
    # VALIDATION ERRORS
    # ─────────────────────────────────────────────────────────────
    elif isinstance(exc, RequestValidationError):
        errors = []
        for err in exc.errors():
            errors.append({
                "field": ".".join(str(x) for x in err["loc"][1:]),
                "message": err["msg"],
                "type": err["type"]
            })
        
        logger.warning(
            f"[{request_id}] Validation Error",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "errors_count": len(errors),
            }
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse.build(
                status_code=422,
                message="Invalid request data",
                error_code="VALIDATION_ERROR",
                details={"errors": errors},
                request_id=request_id
            )
        )
    
    # ─────────────────────────────────────────────────────────────
    # AUTHENTICATION ERRORS
    # ─────────────────────────────────────────────────────────────
    elif isinstance(exc, JWTError):
        logger.warning(
            f"[{request_id}] JWT Error",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "client": client,
            }
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorResponse.build(
                status_code=401,
                message="Invalid or expired authentication token",
                error_code="AUTHENTICATION_ERROR",
                request_id=request_id
            )
        )
    
    # ─────────────────────────────────────────────────────────────
    # GENERIC ERRORS
    # ─────────────────────────────────────────────────────────────
    else:
        logger.error(
            f"[{request_id}] Unhandled Exception",
            extra={
                "request_id": request_id,
                "method": method,
                "path": path,
                "client": client,
                "exc_type": type(exc).__name__,
            },
            exc_info=exc
        )
        await send_error_to_admins(
            title="Unhandled Exception",
            request_id=request_id,
            method=method,
            path=path,
            client=client,
            exc_type=type(exc).__name__,
            details=format_details_for_alert(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse.build(
                status_code=500,
                message="Internal server error",
                error_code="INTERNAL_ERROR",
                request_id=request_id
            )
        )


async def order_flow_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Biznes qoidasi buzilishi (`OrderFlowError`) → **400 Bad Request**.

    Ilgari bunday handler yo'q edi va `OrderFlowError` tutib olinmagan har qanday
    joyda (masalan `Admin_panel/router.py` dagi status o'zgartirish) yuqoridagi
    `Exception` handleriga tushib, mijozga **500 Internal Server Error** qaytarardi.
    Holbuki bu server nosozligi emas — mijoz noto'g'ri o'tish so'ragan.

    Javob shakli `services/problems.py` dagi bilan bir xil (`detail.message` +
    `detail.errors[]`), shunda WebApp'dagi bitta parser hamma joyda ishlaydi
    (`Frontend/src/api/client.ts`).
    """
    request_id = str(uuid.uuid4())
    message = str(exc)

    logger.info(
        f"[{request_id}] Order flow rejected",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "code": getattr(exc, "code", "ORDER_FLOW_ERROR"),
        },
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": {
                "message": message,
                "errors": [
                    {
                        "code": getattr(exc, "code", "ORDER_FLOW_ERROR"),
                        "message": message,
                        **(exc.context() if hasattr(exc, "context") else {}),
                    }
                ],
            },
            "request_id": request_id,
        },
    )


def setup_error_handlers(app: FastAPI):
    """FastAPI'ga error handlers'ni qo'shish."""
    from starlette.middleware.base import BaseHTTPMiddleware

    from services.order_flow import OrderFlowError
    
    class RequestIdMiddleware(BaseHTTPMiddleware):
        """Har javobga X-Request-ID qo'shadi; access log uvicorn'da chiqadi."""

        async def dispatch(self, request: Request, call_next):
            request_id = str(uuid.uuid4())
            try:
                response = await call_next(request)
                response.headers["X-Request-ID"] = request_id
                return response
            except Exception as exc:
                await send_error_to_admins(
                    title="Unhandled Exception (middleware)",
                    request_id=request_id,
                    method=request.method,
                    path=request.url.path,
                    client=request.client.host if request.client else "unknown",
                    exc_type=type(exc).__name__,
                    details=format_details_for_alert(exc),
                )
                raise
    
    # Aniqroq handler oldin qidiriladi (Starlette istisno MRO'si bo'yicha tanlaydi),
    # shuning uchun `OrderFlowError` umumiy `Exception` handleriga tushmaydi.
    app.add_exception_handler(OrderFlowError, order_flow_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_middleware(RequestIdMiddleware)




