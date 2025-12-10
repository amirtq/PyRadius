"""
Statistics Collector (Backward Compatibility Wrapper)

This module re-exports the stats collection functions from the scheduler app
for backward compatibility. New code should import directly from
scheduler.jobs.stats instead.
"""

# Re-export from scheduler.jobs.stats for backward compatibility
from scheduler.jobs.stats import (
    collect_server_active_sessions,
    collect_server_total_traffic,
    collect_users_active_sessions,
    collect_users_total_traffic,
)

__all__ = [
    'collect_server_active_sessions',
    'collect_server_total_traffic',
    'collect_users_active_sessions',
    'collect_users_total_traffic',
]
