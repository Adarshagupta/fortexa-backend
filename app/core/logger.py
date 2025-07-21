import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from app.core.config import settings

# Create logger
logger = logging.getLogger("fortexa")
logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

# Create console handler
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))

# Create formatter
formatter = logging.Formatter(
    fmt=settings.LOG_FORMAT,
    datefmt="%Y-%m-%d %H:%M:%S"
)

console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Prevent duplicate logs
logger.propagate = False

class CustomLogger:
    """Custom logger with additional functionality"""
    
    def __init__(self, name: str = "fortexa"):
        self.logger = logging.getLogger(name)
    
    def info(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log info message"""
        self.logger.info(message, extra=extra)
    
    def error(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log error message"""
        self.logger.error(message, extra=extra)
    
    def warning(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log warning message"""
        self.logger.warning(message, extra=extra)
    
    def debug(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log debug message"""
        self.logger.debug(message, extra=extra)
    
    def critical(self, message: str, extra: Optional[Dict[str, Any]] = None):
        """Log critical message"""
        self.logger.critical(message, extra=extra)
    
    def log_user_action(self, user_id: str, action: str, details: Optional[Dict[str, Any]] = None):
        """Log user action for audit trail"""
        log_data = {
            "user_id": user_id,
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
        self.info(f"User action: {action}", extra=log_data)
    
    def log_api_request(self, method: str, path: str, user_id: Optional[str] = None, 
                       response_time: Optional[float] = None, status_code: Optional[int] = None):
        """Log API request"""
        log_data = {
            "method": method,
            "path": path,
            "user_id": user_id,
            "response_time": response_time,
            "status_code": status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.info(f"API {method} {path}", extra=log_data)
    
    def log_security_event(self, event_type: str, user_id: Optional[str] = None, 
                          details: Optional[Dict[str, Any]] = None):
        """Log security event"""
        log_data = {
            "event_type": event_type,
            "user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
        self.warning(f"Security event: {event_type}", extra=log_data)
    
    def log_database_operation(self, operation: str, table: str, 
                             details: Optional[Dict[str, Any]] = None):
        """Log database operation"""
        log_data = {
            "operation": operation,
            "table": table,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {}
        }
        self.debug(f"DB {operation} on {table}", extra=log_data)

# Create custom logger instance
custom_logger = CustomLogger() 