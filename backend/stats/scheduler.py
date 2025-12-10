"""
Statistics Scheduler (Backward Compatibility Wrapper)

This module re-exports the scheduler functions from the scheduler app
for backward compatibility. New code should import directly from
scheduler.scheduler instead.
"""

# Re-export from scheduler.scheduler for backward compatibility
from scheduler.scheduler import (
    get_scheduler,
    start_scheduler,
    stop_scheduler,
    is_scheduler_running,
    get_scheduler_jobs,
)

__all__ = [
    'get_scheduler',
    'start_scheduler',
    'stop_scheduler',
    'is_scheduler_running',
    'get_scheduler_jobs',
]
