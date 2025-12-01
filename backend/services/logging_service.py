"""Service for structured logging"""
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from contextvars import ContextVar

# Context variable for correlation ID
correlation_id: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class StructuredJSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add correlation ID if available
        corr_id = correlation_id.get()
        if corr_id:
            log_data["correlation_id"] = corr_id
        
        # Add request ID if available
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        # Add execution context if available
        if hasattr(record, "execution_id"):
            log_data["execution_id"] = record.execution_id
        if hasattr(record, "workflow_id"):
            log_data["workflow_id"] = record.workflow_id
        if hasattr(record, "agent_id"):
            log_data["agent_id"] = record.agent_id
        
        # Add any extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def setup_structured_logging(
    log_level: str = "INFO",
    use_json: bool = True
) -> None:
    """
    Setup structured logging.
    
    Args:
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json: Whether to use JSON formatting
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    
    if use_json:
        formatter = StructuredJSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)


def log_execution_event(
    logger: logging.Logger,
    level: str,
    message: str,
    execution_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    extra_fields: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an execution event with structured data.
    
    Args:
        logger: Logger instance
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        message: Log message
        execution_id: Optional execution ID
        workflow_id: Optional workflow ID
        agent_id: Optional agent ID
        extra_fields: Optional extra fields to include
    """
    log_method = getattr(logger, level.lower(), logger.info)
    
    # Create extra dict for structured logging
    extra = {}
    if execution_id:
        extra["execution_id"] = execution_id
    if workflow_id:
        extra["workflow_id"] = workflow_id
    if agent_id:
        extra["agent_id"] = agent_id
    if extra_fields:
        extra["extra_fields"] = extra_fields
    
    log_method(message, extra=extra)


def set_correlation_id(corr_id: str) -> None:
    """Set correlation ID in context"""
    correlation_id.set(corr_id)


def get_correlation_id() -> Optional[str]:
    """Get correlation ID from context"""
    return correlation_id.get()


class ExecutionLogger:
    """Logger for execution-specific logging"""
    
    def __init__(
        self,
        execution_id: str,
        workflow_id: Optional[str] = None,
        logger_name: str = "execution"
    ):
        self.execution_id = execution_id
        self.workflow_id = workflow_id
        self.logger = logging.getLogger(logger_name)
    
    def debug(self, message: str, agent_id: Optional[str] = None, **kwargs):
        """Log debug message"""
        log_execution_event(
            self.logger,
            "DEBUG",
            message,
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
            agent_id=agent_id,
            extra_fields=kwargs
        )
    
    def info(self, message: str, agent_id: Optional[str] = None, **kwargs):
        """Log info message"""
        log_execution_event(
            self.logger,
            "INFO",
            message,
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
            agent_id=agent_id,
            extra_fields=kwargs
        )
    
    def warning(self, message: str, agent_id: Optional[str] = None, **kwargs):
        """Log warning message"""
        log_execution_event(
            self.logger,
            "WARNING",
            message,
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
            agent_id=agent_id,
            extra_fields=kwargs
        )
    
    def error(self, message: str, agent_id: Optional[str] = None, **kwargs):
        """Log error message"""
        log_execution_event(
            self.logger,
            "ERROR",
            message,
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
            agent_id=agent_id,
            extra_fields=kwargs
        )
    
    def critical(self, message: str, agent_id: Optional[str] = None, **kwargs):
        """Log critical message"""
        log_execution_event(
            self.logger,
            "CRITICAL",
            message,
            execution_id=self.execution_id,
            workflow_id=self.workflow_id,
            agent_id=agent_id,
            extra_fields=kwargs
        )

