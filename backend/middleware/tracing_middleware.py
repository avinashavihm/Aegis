"""Middleware for distributed tracing"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from typing import Callable
from backend.services.tracing_service import get_tracer, extract_trace_context, create_trace_context
import logging

logger = logging.getLogger(__name__)


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware to add distributed tracing to requests"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        tracer = get_tracer()
        
        # Extract trace context from headers
        headers = dict(request.headers)
        trace_context = extract_trace_context(headers)
        
        if trace_context:
            # Continue existing trace
            span = tracer.start_span(
                f"{request.method} {request.url.path}",
                parent_span_id=trace_context["span_id"],
                trace_id=trace_context["trace_id"]
            )
            trace_id = trace_context["trace_id"]
        else:
            # Start new trace
            trace = tracer.start_trace(f"{request.method} {request.url.path}")
            span = trace.spans[0]  # Root span
            trace_id = trace.trace_id
        
        # Add trace context to request state
        request.state.trace_id = trace_id
        request.state.span_id = span.span_id
        
        # Add tags
        span.add_tag("http.method", request.method)
        span.add_tag("http.path", request.url.path)
        span.add_tag("http.query", str(request.query_params))
        
        try:
            response = await call_next(request)
            
            # Add response tags
            span.add_tag("http.status_code", response.status_code)
            span.finish("completed" if response.status_code < 400 else "error")
            
            # Add trace headers to response
            response.headers["X-Trace-ID"] = trace_id
            response.headers["X-Span-ID"] = span.span_id
            
            return response
            
        except Exception as e:
            span.add_tag("error", True)
            span.add_tag("error.message", str(e))
            span.add_log(f"Request failed: {str(e)}", level="error")
            span.finish("error")
            raise

