"""
Centralized logging configuration for Java Unit Test Agent.
Provides colored console output, file rotation, and integration with Sentry.
"""

import logging
import sys
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler
from datetime import datetime
import json


# ANSI color codes
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    
    # Foreground colors
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Background colors
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    LEVEL_COLORS = {
        logging.DEBUG: Colors.CYAN,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.BG_RED + Colors.WHITE + Colors.BOLD,
    }
    
    def format(self, record: logging.LogRecord) -> str:
        # Save original values
        levelname = record.levelname
        name = record.name
        
        # Add color to level name
        if record.levelno in self.LEVEL_COLORS:
            color = self.LEVEL_COLORS[record.levelno]
            record.levelname = f"{color}{levelname}{Colors.RESET}"
        
        # Add color to logger name
        record.name = f"{Colors.BLUE}{name}{Colors.RESET}"
        
        # Format the message
        formatted = super().format(record)
        
        # Restore original values to avoid affecting other handlers
        record.levelname = levelname
        record.name = name
        
        return formatted


class DetailedFormatter(logging.Formatter):
    """Human-readable detailed formatter for file logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # Basic log line
        log_line = f"[{timestamp}] [{record.levelname:8}] [{record.name}] {record.getMessage()}"
        
        # Add location info for warnings and errors
        if record.levelno >= logging.WARNING:
            log_line += f" ({record.module}.{record.funcName}:{record.lineno})"
        
        # Add exception info if present
        if record.exc_info:
            log_line += "\n" + self.formatException(record.exc_info)
        
        return log_line


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data, ensure_ascii=False)


def setup_component_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[str] = None,
    console_output: bool = True,
    environment: str = "development",
    file_format: str = "detailed"  # "detailed" or "json"
) -> logging.Logger:
    """
    Setup a logger for a specific component (API, database, etc.)
    
    Args:
        name: Component name (e.g., 'api', 'qdrant', 'memgraph')
        level: Log level
        log_file: Path to component-specific log file
        console_output: Whether to output to console
        environment: Environment name
        file_format: Format for file logs - "detailed" (human-readable) or "json"
    
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    logger.handlers.clear()
    logger.propagate = False  # Don't propagate to root logger
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        
        if environment == "production":
            console_formatter = JSONFormatter()
        else:
            console_formatter = ColoredFormatter(
                fmt=f"%(asctime)s | %(levelname)-8s | {Colors.MAGENTA}[{name.upper()}]{Colors.RESET} | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
        
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Choose formatter based on file_format parameter
        if file_format == "json":
            file_formatter = JSONFormatter()
        else:
            file_formatter = DetailedFormatter()
        
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    enable_sentry: bool = False,
    sentry_dsn: Optional[str] = None,
    environment: str = "development",
    file_format: str = "detailed"  # "detailed" or "json"
) -> None:
    """
    Configure logging for the application.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (None for no file logging)
        enable_sentry: Whether to enable Sentry integration
        sentry_dsn: Sentry DSN for error tracking
        environment: Environment name (development, production)
        file_format: Format for file logs - "detailed" (human-readable) or "json"
    """
    # Create logs directory if needed
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    if environment == "production":
        # JSON format for production
        console_formatter = JSONFormatter()
    else:
        # Colored format for development
        console_formatter = ColoredFormatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        
        # Use specified format for file logs
        if file_format == "json":
            file_formatter = JSONFormatter()
        else:
            file_formatter = DetailedFormatter()
        
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # Sentry integration
    if enable_sentry and sentry_dsn:
        try:
            import sentry_sdk
            from sentry_sdk.integrations.logging import LoggingIntegration
            
            sentry_logging = LoggingIntegration(
                level=logging.INFO,  # Capture info and above as breadcrumbs
                event_level=logging.ERROR  # Send errors as events
            )
            
            sentry_sdk.init(
                dsn=sentry_dsn,
                environment=environment,
                integrations=[sentry_logging],
                traces_sample_rate=0.1 if environment == "production" else 1.0,
                profiles_sample_rate=0.1 if environment == "production" else 1.0,
            )
            
            root_logger.info("Sentry integration enabled")
        except ImportError:
            root_logger.warning("Sentry SDK not installed, skipping Sentry integration")
        except Exception as e:
            root_logger.error(f"Failed to initialize Sentry: {e}")
    
    # Reduce noise from third-party libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("qdrant_client").setLevel(logging.WARNING)
    
    root_logger.info(f"Logging configured - Level: {level}, Environment: {environment}")


def setup_all_loggers(
    base_level: str = "INFO",
    logs_dir: str = "logs",
    environment: str = "development",
    file_format: str = "detailed"  # "detailed" or "json"
) -> dict:
    """
    Setup all component loggers for the application.
    
    Creates separate log files for:
    - API
    - Qdrant (vector database)
    - SQLite Graph (graph database)
    - Redis (cache)
    
    Args:
        base_level: Base log level for all components
        logs_dir: Directory for log files
        environment: Environment name
        file_format: Format for file logs - "detailed" (human-readable) or "json"
    
    Returns:
        Dictionary of logger instances
    """
    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)
    
    loggers = {}
    
    # API Logger
    loggers['api'] = setup_component_logger(
        name='api',
        level=base_level,
        log_file=f"{logs_dir}/api.log",
        console_output=True,
        environment=environment,
        file_format=file_format
    )
    
    # Qdrant Logger
    loggers['qdrant'] = setup_component_logger(
        name='qdrant',
        level=base_level,
        log_file=f"{logs_dir}/qdrant.log",
        console_output=True,
        environment=environment,
        file_format=file_format
    )
    
    # SQLite Graph Logger (replaces Memgraph)
    loggers['sqlite_graph'] = setup_component_logger(
        name='sqlite_graph',
        level=base_level,
        log_file=f"{logs_dir}/database.log",
        console_output=True,
        environment=environment,
        file_format=file_format
    )
    
    # Redis Logger
    loggers['redis'] = setup_component_logger(
        name='redis',
        level=base_level,
        log_file=f"{logs_dir}/redis.log",
        console_output=True,
        environment=environment,
        file_format=file_format
    )
    
    
    # General database logger
    loggers['database'] = setup_component_logger(
        name='database',
        level=base_level,
        log_file=f"{logs_dir}/database.log",
        console_output=True,
        environment=environment,
        file_format=file_format
    )
    
    # Agents Logger (for IndexerAgent, GeneratorAgent, etc.)
    loggers['agents'] = setup_component_logger(
        name='agents',
        level=base_level,
        log_file=f"{logs_dir}/agents.log",
        console_output=True,
        environment=environment,
        file_format=file_format
    )
    
    return loggers


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    # Check if this is a component logger that was set up
    component_loggers = [
        'api', 'qdrant', 'sqlite_graph', 'redis', 'database', 'agents'
    ]
    
    if name in component_loggers:
        # Return the configured component logger
        return logging.getLogger(name)
    else:
        # Return standard logger
        return logging.getLogger(name)


# Context manager for logging extra fields
class LogContext:
    """Context manager for adding extra fields to logs"""
    
    def __init__(self, logger: logging.Logger, **extra_fields):
        self.logger = logger
        self.extra_fields = extra_fields
        self.old_factory = None
    
    def __enter__(self):
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.extra_fields = self.extra_fields
            return record
        
        logging.setLogRecordFactory(record_factory)
        self.old_factory = old_factory
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.old_factory:
            logging.setLogRecordFactory(self.old_factory)


if __name__ == "__main__":
    # Test logging setup
    setup_logging(level="DEBUG", log_file="logs/test.log", environment="development")
    
    logger = get_logger(__name__)
    
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Test context
    with LogContext(logger, request_id="12345", user_id="user-001"):
        logger.info("Message with extra context")
    
    try:
        raise ValueError("Test exception")
    except Exception:
        logger.exception("An exception occurred")
    
    print("\n✅ Logging test completed. Check logs/test.log")

