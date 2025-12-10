"""
Core Scheduler Module

This module provides the APScheduler-based background scheduler for
running periodic tasks. It manages scheduler lifecycle and job registration.
"""

import logging
import atexit
from typing import Optional, Callable, Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None
_scheduler_started: bool = False


def get_scheduler() -> BackgroundScheduler:
    """
    Get or create the global scheduler instance.
    
    Returns:
        The BackgroundScheduler instance
    """
    global _scheduler
    
    if _scheduler is None:
        # Configure executors with a single thread to avoid race conditions
        executors = {
            'default': ThreadPoolExecutor(1),
        }
        
        # Use in-memory job store
        jobstores = {
            'default': MemoryJobStore(),
        }
        
        # Job defaults - don't allow concurrent execution of same job
        job_defaults = {
            'coalesce': True,  # Merge missed runs into one
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 60,  # Allow 60 seconds delay before considering missed
        }
        
        _scheduler = BackgroundScheduler(
            executors=executors,
            jobstores=jobstores,
            job_defaults=job_defaults,
            timezone='UTC'
        )
        
        # Register shutdown handler
        atexit.register(stop_scheduler)
    
    return _scheduler


def add_job(
    func: Callable,
    job_id: str,
    name: str,
    interval_seconds: int,
    **kwargs: Any
) -> None:
    """
    Add an interval job to the scheduler.
    
    Args:
        func: The function to execute
        job_id: Unique identifier for the job
        name: Human-readable name for the job
        interval_seconds: Interval between job executions
        **kwargs: Additional arguments passed to the job function
    """
    scheduler = get_scheduler()
    
    scheduler.add_job(
        func,
        'interval',
        seconds=interval_seconds,
        id=job_id,
        name=name,
        replace_existing=True,
        **kwargs
    )
    logger.info(f"Job added: {name} (every {interval_seconds}s)")


def start_scheduler() -> bool:
    """
    Start the scheduler with all configured jobs.
    
    Returns:
        True if scheduler was started, False if already running
    """
    global _scheduler_started
    
    if _scheduler_started:
        logger.debug("Scheduler already started")
        return False
    
    try:
        # Register all jobs
        _register_cleanup_jobs()
        _register_stats_jobs()
        _register_session_buffer_jobs()
        
        # Start the scheduler
        scheduler = get_scheduler()
        scheduler.start()
        _scheduler_started = True
        
        logger.info("Scheduler started successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")
        return False


def _register_cleanup_jobs() -> None:
    """Register all cleanup jobs with the scheduler."""
    from django.conf import settings
    from scheduler.jobs.cleanup import (
        cleanup_radius_logs,
        cleanup_dead_sessions,
        cleanup_inactive_sessions,
    )
    
    cleanup_config = getattr(settings, 'CLEANUP_CONFIG', {})
    
    # Log cleanup - runs every 5 minutes by default
    log_cleanup_interval = cleanup_config.get('LOG_INTERVAL', 300)
    add_job(
        cleanup_radius_logs,
        job_id='cleanup_radius_logs',
        name='Cleanup Radius Logs',
        interval_seconds=log_cleanup_interval
    )
    
    # Dead session cleanup - runs every 5 minutes by default
    dead_session_interval = cleanup_config.get('DEAD_SESSION_INTERVAL', 300)
    add_job(
        cleanup_dead_sessions,
        job_id='cleanup_dead_sessions',
        name='Cleanup Dead Sessions',
        interval_seconds=dead_session_interval
    )
    
    # Inactive session cleanup - runs every hour by default
    inactive_session_interval = cleanup_config.get('INACTIVE_SESSION_INTERVAL', 3600)
    add_job(
        cleanup_inactive_sessions,
        job_id='cleanup_inactive_sessions',
        name='Cleanup Inactive Sessions',
        interval_seconds=inactive_session_interval
    )


def _register_stats_jobs() -> None:
    """Register all statistics collection jobs with the scheduler."""
    from django.conf import settings
    from scheduler.jobs.stats import (
        collect_server_active_sessions,
        collect_server_total_traffic,
        collect_users_active_sessions,
        collect_users_total_traffic,
    )
    
    stats_config = getattr(settings, 'STATS_CONFIG', {})
    
    # Server sessions stats
    server_sessions_interval = stats_config.get('SERVER_SESSIONS_INTERVAL', 300)
    add_job(
        collect_server_active_sessions,
        job_id='collect_server_active_sessions',
        name='Collect Server Active Sessions',
        interval_seconds=server_sessions_interval
    )
    
    # Server traffic stats
    server_traffic_interval = stats_config.get('SERVER_TRAFFIC_INTERVAL', 300)
    add_job(
        collect_server_total_traffic,
        job_id='collect_server_total_traffic',
        name='Collect Server Total Traffic',
        interval_seconds=server_traffic_interval
    )
    
    # User sessions stats
    users_sessions_interval = stats_config.get('USERS_SESSIONS_INTERVAL', 300)
    add_job(
        collect_users_active_sessions,
        job_id='collect_users_active_sessions',
        name='Collect Users Active Sessions',
        interval_seconds=users_sessions_interval
    )
    
    # User traffic stats
    users_traffic_interval = stats_config.get('USERS_TRAFFIC_INTERVAL', 300)
    add_job(
        collect_users_total_traffic,
        job_id='collect_users_total_traffic',
        name='Collect Users Total Traffic',
        interval_seconds=users_traffic_interval
    )


def _register_session_buffer_jobs() -> None:
    """Register session buffer flush job with the scheduler."""
    from django.conf import settings
    from scheduler.jobs.session_buffer import flush_session_buffer
    
    # Get buffer flush interval from settings (default: 5 seconds)
    flush_interval = getattr(settings, 'SESSION_BUFFER_FLUSH_INTERVAL', 5)
    
    add_job(
        flush_session_buffer,
        job_id='flush_session_buffer',
        name='Flush Session Buffer',
        interval_seconds=flush_interval
    )


def stop_scheduler() -> None:
    """
    Stop the scheduler gracefully.
    """
    global _scheduler, _scheduler_started
    
    if _scheduler is not None and _scheduler_started:
        try:
            # Flush session buffer before stopping to prevent data loss
            _flush_session_buffer_on_shutdown()
            
            _scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
        finally:
            _scheduler_started = False


def _flush_session_buffer_on_shutdown() -> None:
    """Flush the session buffer on shutdown to prevent data loss."""
    try:
        from sessions.buffer import get_session_buffer
        buffer = get_session_buffer()
        buffer.shutdown()
    except Exception as e:
        logger.error(f"Error flushing session buffer on shutdown: {e}")


def is_scheduler_running() -> bool:
    """
    Check if the scheduler is currently running.
    
    Returns:
        True if running, False otherwise
    """
    return _scheduler_started and _scheduler is not None and _scheduler.running


def get_scheduler_jobs() -> list:
    """
    Get list of scheduled jobs.
    
    Returns:
        List of job information dictionaries
    """
    if _scheduler is None:
        return []
    
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'name': job.name,
            'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
            'trigger': str(job.trigger),
        })
    
    return jobs
