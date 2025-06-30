"""
Simple logging utilities for MCP dashboard
"""
import logging
import sys
from typing import Any, Dict

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

class EnhancedLogger:
    """Enhanced logger that handles keyword arguments"""
    
    def __init__(self, logger: logging.Logger):
        self._logger = logger
    
    def info(self, message: str, **kwargs):
        extra_info = " ".join([f"{k}={v}" for k, v in kwargs.items()])
        full_message = f"{message} {extra_info}".strip()
        self._logger.info(full_message)
    
    def error(self, message: str, **kwargs):
        extra_info = " ".join([f"{k}={v}" for k, v in kwargs.items()])
        full_message = f"{message} {extra_info}".strip()
        self._logger.error(full_message)
    
    def warning(self, message: str, **kwargs):
        extra_info = " ".join([f"{k}={v}" for k, v in kwargs.items()])
        full_message = f"{message} {extra_info}".strip()
        self._logger.warning(full_message)
    
    def debug(self, message: str, **kwargs):
        extra_info = " ".join([f"{k}={v}" for k, v in kwargs.items()])
        full_message = f"{message} {extra_info}".strip()
        self._logger.debug(full_message)

def get_logger(name: str) -> EnhancedLogger:
    """Get a logger instance"""
    base_logger = logging.getLogger(name)
    return EnhancedLogger(base_logger)

def log_data_ingestion(source: str, count: int, **kwargs):
    """Log data ingestion events"""
    logger = get_logger("data_ingestion")
    extra_info = " ".join([f"{k}={v}" for k, v in kwargs.items()])
    logger.info(f"Ingested {count} items from {source} {extra_info}")