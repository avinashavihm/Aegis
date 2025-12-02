"""Service for distributed tracing"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import uuid4
import time
import logging

logger = logging.getLogger(__name__)


class TraceSpan:
    """Represents a span in a distributed trace"""
    
    def __init__(
        self,
        trace_id: str,
        span_id: str,
        operation_name: str,
        parent_span_id: Optional[str] = None
    ):
        self.trace_id = trace_id
        self.span_id = span_id
        self.operation_name = operation_name
        self.parent_span_id = parent_span_id
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
        self.duration_ms: Optional[float] = None
        self.tags: Dict[str, Any] = {}
        self.logs: List[Dict[str, Any]] = []
        self.status = "started"
    
    def finish(self, status: str = "completed") -> None:
        """Finish the span"""
        self.end_time = datetime.utcnow()
        duration = (self.end_time - self.start_time).total_seconds() * 1000
        self.duration_ms = duration
        self.status = status
    
    def add_tag(self, key: str, value: Any) -> None:
        """Add a tag to the span"""
        self.tags[key] = value
    
    def add_log(self, message: str, level: str = "info", **kwargs) -> None:
        """Add a log entry to the span"""
        self.logs.append({
            "message": message,
            "level": level,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "tags": self.tags,
            "logs": self.logs
        }


class Trace:
    """Represents a complete distributed trace"""
    
    def __init__(self, trace_id: str, root_operation: str):
        self.trace_id = trace_id
        self.root_operation = root_operation
        self.spans: List[TraceSpan] = []
        self.start_time = datetime.utcnow()
        self.end_time: Optional[datetime] = None
    
    def add_span(self, span: TraceSpan) -> None:
        """Add a span to the trace"""
        self.spans.append(span)
    
    def finish(self) -> None:
        """Finish the trace"""
        self.end_time = datetime.utcnow()
        # Finish any unfinished spans
        for span in self.spans:
            if not span.end_time:
                span.finish()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary"""
        return {
            "trace_id": self.trace_id,
            "root_operation": self.root_operation,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "spans": [span.to_dict() for span in self.spans],
            "span_count": len(self.spans)
        }


class Tracer:
    """Distributed tracer"""
    
    def __init__(self):
        self.traces: Dict[str, Trace] = {}
        self.active_spans: Dict[str, TraceSpan] = {}  # span_id -> span
    
    def start_trace(self, operation_name: str, trace_id: Optional[str] = None) -> Trace:
        """Start a new trace"""
        if not trace_id:
            trace_id = str(uuid4())
        
        trace = Trace(trace_id, operation_name)
        self.traces[trace_id] = trace
        
        # Create root span
        root_span = self.start_span(trace_id, operation_name, trace_id=trace_id)
        trace.add_span(root_span)
        
        return trace
    
    def start_span(
        self,
        operation_name: str,
        parent_span_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> TraceSpan:
        """Start a new span"""
        span_id = str(uuid4())
        
        if not trace_id and parent_span_id:
            # Find trace from parent span
            parent_span = self.active_spans.get(parent_span_id)
            if parent_span:
                trace_id = parent_span.trace_id
        
        if not trace_id:
            # Create new trace
            trace = self.start_trace(operation_name)
            trace_id = trace.trace_id
        else:
            # Add to existing trace
            trace = self.traces.get(trace_id)
            if not trace:
                trace = Trace(trace_id, operation_name)
                self.traces[trace_id] = trace
        
        span = TraceSpan(trace_id, span_id, operation_name, parent_span_id)
        self.active_spans[span_id] = span
        trace.add_span(span)
        
        return span
    
    def finish_span(self, span_id: str, status: str = "completed") -> Optional[TraceSpan]:
        """Finish a span"""
        span = self.active_spans.pop(span_id, None)
        if span:
            span.finish(status)
        return span
    
    def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Get a trace by ID"""
        return self.traces.get(trace_id)
    
    def get_traces(
        self,
        operation_name: Optional[str] = None,
        limit: int = 100
    ) -> List[Trace]:
        """Get traces, optionally filtered by operation name"""
        traces = list(self.traces.values())
        
        if operation_name:
            traces = [t for t in traces if t.root_operation == operation_name]
        
        # Sort by start time (newest first)
        traces.sort(key=lambda t: t.start_time, reverse=True)
        
        return traces[:limit]


# Global tracer instance
_tracer = Tracer()


def get_tracer() -> Tracer:
    """Get the global tracer instance"""
    return _tracer


def create_trace_context(trace_id: str, span_id: str) -> Dict[str, str]:
    """Create trace context for propagation"""
    return {
        "trace_id": trace_id,
        "span_id": span_id
    }


def extract_trace_context(headers: Dict[str, str]) -> Optional[Dict[str, str]]:
    """Extract trace context from headers"""
    trace_id = headers.get("X-Trace-ID")
    span_id = headers.get("X-Span-ID")
    
    if trace_id and span_id:
        return {
            "trace_id": trace_id,
            "span_id": span_id
        }
    
    return None

