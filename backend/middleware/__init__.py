"""Middleware for request tracking and logging"""
import uuid
import time
import logging
import json
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from backend.services.logging_service import set_correlation_id, get_correlation_id

logger = logging.getLogger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add request ID and correlation ID to each request"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Set correlation ID in context (use request ID as correlation ID)
        set_correlation_id(request_id)
        
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            # Clear correlation ID after request
            set_correlation_id(None)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log requests and responses with structured logging"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = getattr(request.state, "request_id", "unknown")
        correlation_id = get_correlation_id() or request_id
        start_time = time.time()
        
        # Log request with structured data
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={
                "request_id": request_id,
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": request.client.host if request.client else None,
            }
        )
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log response with structured data
            logger.info(
                f"Response: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": process_time,
                }
            )
            
            response.headers["X-Process-Time"] = str(process_time)
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                f"Error processing request: {request.method} {request.url.path}",
                extra={
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "process_time": process_time,
                },
                exc_info=True
            )
            raise

