"""
Logger Configuration for PhoneTracker CLI
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


def setup_logger(
    name: str = 'phonetracker',
    log_file: Optional[Path] = None,
    level: int = logging.INFO,
    console_output: bool = True
) -> logging.Logger:
    """
    Set up a logger with file and/or console handlers.
    
    Args:
        name: Logger name
        log_file: Path to log file (optional)
        level: Logging level
        console_output: Whether to also log to console
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger


def get_logger(name: str = 'phonetracker') -> logging.Logger:
    """
    Get the application logger.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class TrackingLogger:
    """
    Specialized logger for tracking operations.
    
    Provides structured logging for tracking events.
    """
    
    def __init__(self, log_file: Optional[Path] = None):
        self.logger = setup_logger(
            name='phonetracker.tracking',
            log_file=log_file,
            console_output=False
        )
    
    def log_track_attempt(
        self,
        phone_number: str,
        method: str,
        success: bool,
        location: Optional[dict] = None,
        error: Optional[str] = None
    ):
        """Log a tracking attempt."""
        message = {
            'event': 'track_attempt',
            'phone_number': phone_number,
            'method': method,
            'success': success,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        if location:
            message['location'] = {
                'lat': location.get('latitude'),
                'lng': location.get('longitude'),
                'accuracy': location.get('accuracy')
            }
        
        if error:
            message['error'] = error
        
        if success:
            self.logger.info(str(message))
        else:
            self.logger.warning(str(message))
    
    def log_config_change(self, key: str, user: str):
        """Log a configuration change."""
        self.logger.info(f"Config changed: {key} by {user}")
    
    def log_error(self, error: str, context: Optional[dict] = None):
        """Log an error."""
        message = f"Error: {error}"
        if context:
            message += f" | Context: {context}"
        self.logger.error(message)
