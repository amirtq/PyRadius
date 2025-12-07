"""
Statistics Scheduler

This module provides the APScheduler-based background scheduler for
collecting statistics at configurable intervals. The scheduler runs
in a single thread, avoiding race conditions.
"""

import logging
import atexit
from typing import Optional

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


def start_scheduler() -> bool:
    """
    Start the statistics scheduler if not already running.
    Adds jobs based on configuration from settings.
    
    Returns:
        True if scheduler was started, False if already running
    """
    global _scheduler_started
    
    if _scheduler_started:
        logger.debug("Stats scheduler already started")
        return False
    
    try:
        from django.conf import settings
        from stats.collector import (
            collect_server_active_sessions,
            collect_server_total_traffic,
            collect_users_active_sessions,
            collect_users_total_traffic,
        )
        
        scheduler = get_scheduler()
        stats_config = getattr(settings, 'STATS_CONFIG', {})
        
        # Get intervals (default to 300 seconds = 5 minutes)
        server_sessions_interval = stats_config.get('SERVER_SESSIONS_INTERVAL', 300)
        server_traffic_interval = stats_config.get('SERVER_TRAFFIC_INTERVAL', 300)
        users_sessions_interval = stats_config.get('USERS_SESSIONS_INTERVAL', 300)
        users_traffic_interval = stats_config.get('USERS_TRAFFIC_INTERVAL', 300)
        
        # Add jobs for each stat type
        scheduler.add_job(
            collect_server_active_sessions,
            'interval',
            seconds=server_sessions_interval,
            id='collect_server_active_sessions',
            name='Collect Server Active Sessions',
            replace_existing=True
        )
        logger.info(f"Stats job added: Server Active Sessions (every {server_sessions_interval}s)")
        
        scheduler.add_job(
            collect_server_total_traffic,
            'interval',
            seconds=server_traffic_interval,
            id='collect_server_total_traffic',
            name='Collect Server Total Traffic',
            replace_existing=True
        )
        logger.info(f"Stats job added: Server Total Traffic (every {server_traffic_interval}s)")
        
        scheduler.add_job(
            collect_users_active_sessions,
            'interval',
            seconds=users_sessions_interval,
            id='collect_users_active_sessions',
            name='Collect Users Active Sessions',
            replace_existing=True
        )
        logger.info(f"Stats job added: Users Active Sessions (every {users_sessions_interval}s)")
        
        scheduler.add_job(
            collect_users_total_traffic,
            'interval',
            seconds=users_traffic_interval,
            id='collect_users_total_traffic',
            name='Collect Users Total Traffic',
            replace_existing=True
        )
        logger.info(f"Stats job added: Users Total Traffic (every {users_traffic_interval}s)")
        
        # Start the scheduler
        scheduler.start()
        _scheduler_started = True
        
        logger.info("Stats scheduler started successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error starting stats scheduler: {e}")
        return False


def stop_scheduler() -> None:
    """
    Stop the statistics scheduler gracefully.
    """
    global _scheduler, _scheduler_started
    
    if _scheduler is not None and _scheduler_started:
        try:
            _scheduler.shutdown(wait=False)
            logger.info("Stats scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping stats scheduler: {e}")
        finally:
            _scheduler_started = False


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
