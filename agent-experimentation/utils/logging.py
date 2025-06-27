"""
Logging configuration for the application
"""
import logging
import structlog
from typing import Any, Dict
import sys
from pathlib import Path

from config import settings


def setup_logging():
    """Setup structured logging for the application"""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if not settings.app.debug else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if settings.app.debug else logging.INFO,
    )
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Add file handler for production
    if not settings.app.debug:
        file_handler = logging.FileHandler("logs/app.log")
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logging.getLogger().addHandler(file_handler)


def get_logger(name: str = None) -> structlog.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class"""
    
    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger for this class"""
        return get_logger(self.__class__.__name__)


def log_api_request(method: str, path: str, **kwargs) -> Dict[str, Any]:
    """Log API request with structured data"""
    return {
        "event": "api_request",
        "method": method,
        "path": path,
        **kwargs
    }


def log_database_operation(operation: str, table: str, **kwargs) -> Dict[str, Any]:
    """Log database operation with structured data"""
    return {
        "event": "database_operation",
        "operation": operation,
        "table": table,
        **kwargs
    }


def log_ai_operation(model: str, operation: str, **kwargs) -> Dict[str, Any]:
    """Log AI/ML operation with structured data"""
    return {
        "event": "ai_operation",
        "model": model,
        "operation": operation,
        **kwargs
    }


def log_alert_triggered(alert_type: str, severity: str, **kwargs) -> Dict[str, Any]:
    """Log alert trigger with structured data"""
    return {
        "event": "alert_triggered",
        "alert_type": alert_type,
        "severity": severity,
        **kwargs
    }


def log_data_ingestion(source: str, records_processed: int, **kwargs) -> Dict[str, Any]:
    """Log data ingestion with structured data"""
    return {
        "event": "data_ingestion",
        "source": source,
        "records_processed": records_processed,
        **kwargs
    }