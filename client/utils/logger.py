"""
Centralized Logging System for PDFLib Client

Provides structured logging with:
- File rotation (max 10MB, 5 backup files)
- Multiple log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Console and file output
- Structured format with timestamps
"""

import logging
import sys
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime


class LogFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
    }
    RESET = '\033[0m'
    
    # Format strings
    CONSOLE_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
    FILE_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)-30s | %(funcName)-25s | Line %(lineno)-4d | %(message)s'
    
    def __init__(self, use_color=True):
        super().__init__()
        self.use_color = use_color
        self._console_fmt = logging.Formatter(self.CONSOLE_FORMAT)
        self._file_fmt = logging.Formatter(self.FILE_FORMAT)
    
    def format(self, record):
        # Use file formatter for file handlers
        if not self.use_color:
            return self._file_fmt.format(record)
        
        # Use colored formatter for console
        levelname = record.levelname
        if self.use_color and levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        return self._console_fmt.format(record)


def setup_logging(
    log_dir: str = "logs",
    log_level: str = "DEBUG",
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    console_output: bool = True
) -> logging.Logger:
    """
    Setup centralized logging for the application.
    
    Args:
        log_dir: Directory to store log files
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
        console_output: Whether to output logs to console
    
    Returns:
        Root logger for the application
    """
    # Create log directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Create logs for today
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = log_path / f"pdflib_{today}.log"
    
    # Get root logger
    logger = logging.getLogger("pdflib")
    logger.setLevel(getattr(logging, log_level.upper(), logging.DEBUG))
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # File handler with rotation
    try:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8',
            delay=True
        )
        file_handler.setLevel(logging.DEBUG)  # Log everything to file
        file_handler.setFormatter(LogFormatter(use_color=False))
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"Warning: Could not create file logger: {e}")
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        console_handler.setFormatter(LogFormatter(use_color=True))
        logger.addHandler(console_handler)
    
    # Log startup info
    logger.info("=" * 80)
    logger.info(f"PDFLib Application Started")
    logger.info(f"Log file: {log_file.absolute()}")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Platform: {sys.platform}")
    logger.info("=" * 80)
    
    # Log unhandled exceptions
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            return
        logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    sys.excepthook = handle_exception
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Module name (e.g., "client.main_window")
    
    Returns:
        Logger instance
    """
    return logging.getLogger(f"pdflib.{name}")


# Convenience functions for quick logging
def log_debug(module: str, message: str, **kwargs):
    """Log debug message"""
    logger = get_logger(module)
    if kwargs:
        logger.debug(f"{message} | {kwargs}")
    else:
        logger.debug(message)


def log_info(module: str, message: str, **kwargs):
    """Log info message"""
    logger = get_logger(module)
    if kwargs:
        logger.info(f"{message} | {kwargs}")
    else:
        logger.info(message)


def log_warning(module: str, message: str, **kwargs):
    """Log warning message"""
    logger = get_logger(module)
    if kwargs:
        logger.warning(f"{message} | {kwargs}")
    else:
        logger.warning(message)


def log_error(module: str, message: str, exc_info=False, **kwargs):
    """Log error message"""
    logger = get_logger(module)
    if kwargs:
        message = f"{message} | {kwargs}"
    if exc_info:
        logger.error(message, exc_info=True)
    else:
        logger.error(message)


def log_critical(module: str, message: str, exc_info=False, **kwargs):
    """Log critical message"""
    logger = get_logger(module)
    if kwargs:
        message = f"{message} | {kwargs}"
    if exc_info:
        logger.critical(message, exc_info=True)
    else:
        logger.critical(message)


# Initialize logging when module is imported
# This ensures logging is available throughout the application
try:
    _root_logger = setup_logging()
except Exception as e:
    print(f"Failed to initialize logging: {e}")
    _root_logger = None
