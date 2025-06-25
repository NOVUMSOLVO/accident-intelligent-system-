import json
import sys
from datetime import datetime
from typing import Any, Dict

from loguru import logger

from .config import load_config

#!/usr/bin/env python3
"""
Logging Configuration
Provides structured logging for the application
"""


class JSONFormatter:
    """Custom JSON formatter for structured logging"""

    def format(self, record: Dict[str, Any]) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record["level"].name,
            "logger": record["name"],
            "message": record["message"],
            "module": record["module"],
            "function": record["function"],
            "line": record["line"],
        }

        # Add extra fields if present
        if "extra" in record and record["extra"]:
            log_entry.update(record["extra"])

        # Add exception info if present
        if record["exception"]:
            log_entry["exception"] = {
                "type": record["exception"].type.__name__,
                "value": str(record["exception"].value),
                "traceback": record["exception"].traceback,
            }

        return json.dumps(log_entry, ensure_ascii=False)


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Setup application logging configuration"""

    # Remove default logger
    logger.remove()

    if log_format.lower() == "json":
        # JSON structured logging
        logger.add(
            sys.stdout,
            format=JSONFormatter().format,
            level=log_level.upper(),
            serialize=False,
            backtrace=True,
            diagnose=True,
        )
    else:
        # Human-readable format
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )

        logger.add(
            sys.stdout,
            format=format_string,
            level=log_level.upper(),
            colorize=True,
            backtrace=True,
            diagnose=True,
        )

    # Add file logging for errors
    logger.add(
        "logs/error.log",
        format=(
            JSONFormatter().format if log_format.lower() == "json" else format_string
        ),
        level="ERROR",
        rotation="10 MB",
        retention="30 days",
        compression="gz",
        serialize=False,
    )

    # Add file logging for all messages
    logger.add(
        "logs/app.log",
        format=(
            JSONFormatter().format if log_format.lower() == "json" else format_string
        ),
        level=log_level.upper(),
        rotation="50 MB",
        retention="7 days",
        compression="gz",
        serialize=False,
    )


def get_logger(name: str) -> logger:
    """Get a logger instance with the specified name"""
    return logger.bind(name=name)


class LoggerMixin:
    """Mixin class to add logging capabilities to any class"""

    @property
    def logger(self):
        """Get logger for this class"""
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger


def log_function_call(func):
    """Decorator to log function calls with parameters and execution time"""

    def wrapper(*args, **kwargs):
        func_logger = get_logger(f"{func.__module__}.{func.__name__}")

        # Log function entry
        func_logger.debug(
            f"Calling {func.__name__}",
            extra={
                "function": func.__name__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()),
            },
        )

        start_time = datetime.utcnow()

        try:
            result = func(*args, **kwargs)

            # Log successful completion
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            func_logger.debug(
                f"Completed {func.__name__}",
                extra={
                    "function": func.__name__,
                    "execution_time_seconds": execution_time,
                    "status": "success",
                },
            )

            return result

        except Exception as e:
            # Log exception
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            func_logger.error(
                f"Error in {func.__name__}: {str(e)}",
                extra={
                    "function": func.__name__,
                    "execution_time_seconds": execution_time,
                    "status": "error",
                    "error_type": type(e).__name__,
                },
            )
            raise

    return wrapper


class StructuredLogger:
    """Enhanced logger with structured logging capabilities"""

    def __init__(self, name: str):
        self.logger = get_logger(name)
        self.name = name

    def info(self, message: str, **kwargs):
        """Log info message with structured data"""
        self.logger.info(message, extra=kwargs)

    def debug(self, message: str, **kwargs):
        """Log debug message with structured data"""
        self.logger.debug(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with structured data"""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs):
        """Log error message with structured data"""
        self.logger.error(message, extra=kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message with structured data"""
        self.logger.critical(message, extra=kwargs)

    def log_api_call(
        self,
        api_name: str,
        endpoint: str,
        status_code: int,
        response_time: float,
        **kwargs,
    ):
        """Log API call with standardized structure"""
        self.logger.info(
            f"API call to {api_name}",
            extra={
                "api_name": api_name,
                "endpoint": endpoint,
                "status_code": status_code,
                "response_time_seconds": response_time,
                "event_type": "api_call",
                **kwargs,
            },
        )

    def log_data_processing(
        self,
        operation: str,
        input_count: int,
        output_count: int,
        processing_time: float,
        **kwargs,
    ):
        """Log data processing operation"""
        self.logger.info(
            f"Data processing: {operation}",
            extra={
                "operation": operation,
                "input_count": input_count,
                "output_count": output_count,
                "processing_time_seconds": processing_time,
                "event_type": "data_processing",
                **kwargs,
            },
        )

    def log_kafka_event(
        self, topic: str, partition: int, offset: int, event_type: str, **kwargs
    ):
        """Log Kafka-related events"""
        self.logger.info(
            f"Kafka {event_type}",
            extra={
                "topic": topic,
                "partition": partition,
                "offset": offset,
                "event_type": f"kafka_{event_type}",
                **kwargs,
            },
        )

    def log_database_operation(
        self,
        database: str,
        operation: str,
        collection_table: str,
        affected_rows: int,
        execution_time: float,
        **kwargs,
    ):
        """Log database operations"""
        self.logger.info(
            f"Database {operation}",
            extra={
                "database": database,
                "operation": operation,
                "collection_table": collection_table,
                "affected_rows": affected_rows,
                "execution_time_seconds": execution_time,
                "event_type": "database_operation",
                **kwargs,
            },
        )


# Initialize logging on module import

try:
    config = load_config()
    setup_logging(config.log_level, config.log_format)
except Exception:
    # Fallback to basic logging if config fails
    setup_logging("INFO", "text")
