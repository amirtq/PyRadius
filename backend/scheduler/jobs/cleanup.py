"""
Cleanup Jobs

This module contains scheduled jobs for cleaning up old data:
- Log entries
- Dead/stale sessions
- Inactive sessions
"""

import logging

logger = logging.getLogger(__name__)


def cleanup_radius_logs() -> int:
    """
    Clean up old RADIUS log entries based on retention setting.
    
    Keeps only the most recent N log entries where N is configured
    via RADIUS_LOG_RETENTION setting.
    
    Returns:
        Number of log entries deleted
    """
    from django.conf import settings
    from radius.models import RadiusLog
    
    try:
        limit = getattr(settings, 'RADIUS_LOG_RETENTION', 10000)
        
        if not limit or limit <= 0:
            return 0
        
        count = RadiusLog.objects.count()
        
        if count <= limit:
            return 0
        
        # Calculate how many records to delete
        to_delete = count - limit
        
        # Get the ID threshold - records with ID <= this will be deleted
        threshold_record = RadiusLog.objects.order_by('id').values_list(
            'id', flat=True
        )[to_delete - 1:to_delete]
        
        if threshold_record:
            threshold_id = threshold_record[0]
            deleted, _ = RadiusLog.objects.filter(id__lte=threshold_id).delete()
            
            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old log entries")
            
            return deleted
        
        return 0
        
    except Exception as e:
        logger.error(f"Error cleaning up radius logs: {e}")
        return 0


def cleanup_dead_sessions() -> int:
    """
    Clean up dead active sessions that haven't received updates for too long.
    
    A session is considered dead if it hasn't received an accounting update
    within ACCT_INTERIM_INTERVAL * STALE_SESSION_MULTIPLIER seconds.
    
    Returns:
        Number of sessions cleaned up
    """
    from sessions.models import RadiusSession
    
    try:
        count = RadiusSession.cleanup_dead_sessions()
        
        if count > 0:
            logger.info(f"Cleaned up {count} dead sessions")
        
        return count
        
    except Exception as e:
        logger.error(f"Error cleaning up dead sessions: {e}")
        return 0


def cleanup_inactive_sessions() -> int:
    """
    Clean up old inactive (stopped) sessions beyond the retention limit.
    
    Keeps only the most recent N stopped sessions where N is configured
    via RADIUS_INACTIVE_SESSION_DB_RETENTION_LIMIT setting.
    
    Returns:
        Number of sessions deleted
    """
    from django.conf import settings
    from sessions.models import RadiusSession
    
    try:
        limit = settings.RADIUS_CONFIG.get('MAX_INACTIVE_SESSIONS', 100)
        
        # Get all stopped sessions ordered by stop_time desc (newest first)
        qs = RadiusSession.objects.filter(
            status=RadiusSession.STATUS_STOPPED
        ).order_by('-stop_time')
        
        count = qs.count()
        
        if count <= limit:
            return 0
        
        # Get the IDs of sessions to keep (most recent ones)
        keep_ids = list(qs[:limit].values_list('id', flat=True))
        
        # Delete sessions not in the keep list
        deleted, _ = RadiusSession.objects.filter(
            status=RadiusSession.STATUS_STOPPED
        ).exclude(id__in=keep_ids).delete()
        
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old inactive sessions")
        
        return deleted
        
    except Exception as e:
        logger.error(f"Error cleaning up inactive sessions: {e}")
        return 0
