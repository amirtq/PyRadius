"""
Session Buffer Scheduler Jobs

This module provides scheduler jobs for managing the session buffer,
including periodic flushing of buffered operations to the database.
"""

import logging

logger = logging.getLogger(__name__)


def flush_session_buffer() -> None:
    """
    Flush the session buffer to the database.
    
    This job runs periodically (default: every 5 seconds) to write
    buffered session operations (START, UPDATE, STOP) to the database
    in a single transaction, improving performance by reducing I/O.
    """
    try:
        from sessions.buffer import get_session_buffer
        
        buffer = get_session_buffer()
        count = buffer.flush()
        
        if count > 0:
            logger.debug(f"Session buffer flush completed: {count} operations")
            
    except Exception as e:
        logger.error(f"Error flushing session buffer: {e}")
