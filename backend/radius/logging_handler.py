"""
Database Log Handler for RADIUS Server

This module provides a logging handler that stores log messages
in the database. Optimized for MySQL to avoid blocking the
RADIUS authentication/accounting threads.
"""

import logging
import random
import threading

# Track last cleanup time to avoid running on every log emit
_last_cleanup_time = 0
_cleanup_lock = threading.Lock()


class DatabaseLogHandler(logging.Handler):
    """
    A logging handler that stores log messages in the database.
    
    Optimized to:
    - Not block on every log message
    - Use efficient database queries for retention
    - Run cleanup only periodically
    """
    
    # Minimum seconds between cleanup runs
    CLEANUP_INTERVAL = 60
    
    def emit(self, record):
        """
        Emit a log record to the database.
        
        Args:
            record: The log record to emit
        """
        import time
        from .models import RadiusLog
        from django.conf import settings
        
        try:
            msg = self.format(record)
            RadiusLog.objects.create(
                level=record.levelname,
                logger=record.name,
                message=msg
            )
            
            # Run retention logic only periodically to avoid blocking
            self._maybe_run_cleanup(settings)
                
        except Exception:
            self.handleError(record)
    
    def _maybe_run_cleanup(self, settings):
        """
        Run cleanup if enough time has passed since the last cleanup.
        Uses a lock to prevent multiple threads from running cleanup simultaneously.
        """
        import time
        global _last_cleanup_time
        
        current_time = time.time()
        
        # Quick check without lock
        if current_time - _last_cleanup_time < self.CLEANUP_INTERVAL:
            return
        
        # Try to acquire lock without blocking
        if not _cleanup_lock.acquire(blocking=False):
            return
        
        try:
            # Double-check after acquiring lock
            if current_time - _last_cleanup_time < self.CLEANUP_INTERVAL:
                return
            
            limit = getattr(settings, 'RADIUS_LOG_RETENTION', 1000)
            if limit and limit > 0:
                self._run_cleanup(limit)
            
            _last_cleanup_time = current_time
        finally:
            _cleanup_lock.release()
    
    def _run_cleanup(self, limit):
        """
        Clean up old log entries, keeping only the most recent 'limit' entries.
        
        Uses efficient database operations that work well with MySQL.
        
        Args:
            limit: Maximum number of log entries to keep
        """
        from .models import RadiusLog
        from django.db import connection
        
        try:
            # Get total count
            count = RadiusLog.objects.count()
            
            if count <= limit:
                return
            
            # Calculate how many records to delete
            to_delete = count - limit
            
            # Get the ID threshold - delete all records with ID less than or equal to this
            # We order by ID ascending and get the Nth record's ID
            threshold_record = RadiusLog.objects.order_by('id').values_list('id', flat=True)[to_delete - 1:to_delete]
            
            if threshold_record:
                threshold_id = threshold_record[0]
                # Delete all records with ID <= threshold
                # This is much more efficient than excluding a list of IDs
                RadiusLog.objects.filter(id__lte=threshold_id).delete()
                
        except Exception:
            # Silently ignore cleanup errors - logging should not affect main functionality
            pass
