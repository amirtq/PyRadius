"""
Database Log Handler for RADIUS Server

This module provides a logging handler that stores log messages
in the database. The handler only inserts log records - cleanup
is handled by the scheduler app.
"""

import logging


class DatabaseLogHandler(logging.Handler):
    """
    A logging handler that stores log messages in the database.
    
    This handler is optimized for performance - it only inserts log records.
    Cleanup of old logs is handled separately by the scheduler's
    cleanup_radius_logs job.
    """
    
    def emit(self, record):
        """
        Emit a log record to the database.
        
        Args:
            record: The log record to emit
        """
        from .models import RadiusLog
        
        try:
            msg = self.format(record)
            RadiusLog.objects.create(
                level=record.levelname,
                logger=record.name,
                message=msg
            )
        except Exception:
            self.handleError(record)
