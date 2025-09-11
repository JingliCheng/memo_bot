"""
Structured logging configuration for Memo Bot.

This module provides:
- JSON structured logging
- Request correlation IDs
- User ID tracking
- Performance metrics logging
- Exception handling
"""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict

class StructuredFormatter(logging.Formatter):
    """JSON structured log formatter for production logging.
    
    Formats log records as JSON with structured fields for:
    - Request correlation
    - User tracking
    - Performance metrics
    - Error details
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            str: JSON formatted log entry
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if present
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
        if hasattr(record, 'endpoint'):
            log_entry['endpoint'] = record.endpoint
        if hasattr(record, 'request_id'):
            log_entry['request_id'] = record.request_id
        if hasattr(record, 'openai_model'):
            log_entry['openai_model'] = record.openai_model
        if hasattr(record, 'input_tokens'):
            log_entry['input_tokens'] = record.input_tokens
        if hasattr(record, 'output_tokens'):
            log_entry['output_tokens'] = record.output_tokens
        if hasattr(record, 'latency_ms'):
            log_entry['latency_ms'] = record.latency_ms
        if hasattr(record, 'cost_usd'):
            log_entry['cost_usd'] = record.cost_usd
        if hasattr(record, 'rate_limit_key'):
            log_entry['rate_limit_key'] = record.rate_limit_key
        if hasattr(record, 'rate_limit_hit'):
            log_entry['rate_limit_hit'] = record.rate_limit_hit
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

def setup_logging() -> None:
    """Setup structured logging for the application.
    
    Configures:
    - JSON formatter for structured logs
    - Console output handler
    - Suppressed noisy loggers
    """
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(StructuredFormatter())
    
    # Add handler to logger
    logger.addHandler(console_handler)
    
    # Suppress noisy loggers
    logging.getLogger("google.cloud").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

def log_request(level: str, message: str, **kwargs: Any) -> None:
    """Log request with structured data.
    
    Args:
        level: Log level (info, error, warning, etc.)
        message: Log message
        **kwargs: Additional structured fields
    """
    logger = logging.getLogger("memo_bot.request")
    record = logger.makeRecord(
        "memo_bot.request", 
        getattr(logging, level.upper()), 
        "", 0, message, (), None
    )
    
    # Add extra fields
    for key, value in kwargs.items():
        setattr(record, key, value)
    
    logger.handle(record)
