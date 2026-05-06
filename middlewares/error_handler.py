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
import json
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
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=ErrorResponse.build(
                status_code=409,
                message="❌ Database conflict - duplicate entry or invalid reference",
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
                message="❌ Database operation failed",
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
                message="❌ Invalid request data",
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
                message="❌ Invalid or expired authentication token",
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
                message="❌ Internal server error",
                error_code="INTERNAL_ERROR",
                request_id=request_id
            )
        )


class RequestLoggingMiddleware:
    """
    Har bitta request/response'ni log qiladi.
    Performance va debugging uchun foydalaniladi.
    """
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        
        # Request ma'lumotlarini loglash
        logger.info(
            f"📥 {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown",
                "query_params": dict(request.query_params),
            }
        )
        
        try:
            # Request ni process qilish
            response = await call_next(request)
            
            # Response ma'lumotlarini loglash
            logger.info(
                f"📤 {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                }
            )
            
            # Request ID ni response header'iga qo'shish
            response.headers["X-Request-ID"] = request_id
            return response
        
        except Exception as exc:
            logger.error(
                f"❌ {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "exc_type": type(exc).__name__,
                },
                exc_info=exc
            )
            raise


def setup_error_handlers(app: FastAPI):
    """FastAPI'ga error handlers'ni qo'shish."""
    from starlette.middleware.base import BaseHTTPMiddleware
    
    class RequestLoggingHTTPMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            request_id = str(uuid.uuid4())
            
            logger.info(
                f"📥 {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                }
            )
            
            try:
                response = await call_next(request)
                logger.info(
                    f"📤 {request.method} {request.url.path} - {response.status_code}",
                    extra={
                        "request_id": request_id,
                        "status_code": response.status_code,
                    }
                )
                response.headers["X-Request-ID"] = request_id
                return response
            except Exception as exc:
                logger.error(
                    f"❌ {request.method} {request.url.path}",
                    extra={
                        "request_id": request_id,
                        "exc_type": type(exc).__name__,
                    },
                    exc_info=exc
                )
                raise
    
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_middleware(RequestLoggingHTTPMiddleware)


class StructuredFormatter(logging.Formatter):
    """
    JSON format'da logging uchun custom formatter.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Extra fields qo'shish (request_id, user_id, etc.)
        if hasattr(record, "request_id") and record.request_id:
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id") and record.user_id:
            log_data["user_id"] = record.user_id
        if hasattr(record, "method") and record.method:
            log_data["method"] = record.method
        if hasattr(record, "path") and record.path:
            log_data["path"] = record.path
        if hasattr(record, "status_code") and record.status_code:
            log_data["status_code"] = record.status_code
        
        # Exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


def setup_logging(environment: str = "development"):
    """
    Logging'ni sozlash (ENV'ga qarab JSON yoki text format).
    """
    import sys
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove default handlers
    root_logger.handlers.clear()
    
    # Create formatters
    if environment == "production":
        # Production: JSON format to file
        formatter = StructuredFormatter()
        
        # File handler
        file_handler = logging.FileHandler("logs/app.log")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    else:
        # Development: Text format to console with colors
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Set specific loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    logger.info(f"✅ Logging configured for {environment} environment")






