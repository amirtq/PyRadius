"""
Statistics Collector

This module contains the logic for collecting and saving statistics data.
It queries the current state of sessions and users and saves snapshots
to the statistics tables.
"""

import logging
from django.utils import timezone
from django.db.models import Sum

logger = logging.getLogger(__name__)


def collect_server_active_sessions() -> None:
    """
    Collect and save server-wide active session count.
    Queries the RadiusSession table for active sessions and saves to stats.
    """
    try:
        from sessions.models import RadiusSession
        from stats.models import StatsServerActiveSessions
        
        # Count all active sessions
        active_count = RadiusSession.objects.filter(
            status=RadiusSession.STATUS_ACTIVE
        ).count()
        
        # Save the stat
        StatsServerActiveSessions.objects.create(
            timestamp=timezone.now(),
            active_sessions=active_count
        )
        
        logger.debug(f"Stats: Saved server active sessions = {active_count}")
        
    except Exception as e:
        logger.error(f"Error collecting server active sessions: {e}")


def collect_server_total_traffic() -> None:
    """
    Collect and save server-wide total traffic.
    Sums traffic from all RadiusUser records and saves to stats.
    """
    try:
        from users.models import RadiusUser
        from stats.models import StatsServerTotalTraffic
        
        # Sum all user traffic
        totals = RadiusUser.objects.aggregate(
            total_rx=Sum('rx_traffic'),
            total_tx=Sum('tx_traffic'),
            total_traffic=Sum('total_traffic')
        )
        
        # Handle None values (when no users exist)
        total_rx = totals['total_rx'] or 0
        total_tx = totals['total_tx'] or 0
        total_traffic = totals['total_traffic'] or 0
        
        # Save the stat
        StatsServerTotalTraffic.objects.create(
            timestamp=timezone.now(),
            total_rx=total_rx,
            total_tx=total_tx,
            total_traffic=total_traffic
        )
        
        logger.debug(f"Stats: Saved server total traffic = {total_traffic} bytes")
        
    except Exception as e:
        logger.error(f"Error collecting server total traffic: {e}")


def collect_users_active_sessions() -> None:
    """
    Collect and save per-user active session counts.
    For each user with active sessions, saves a record to stats.
    """
    try:
        from sessions.models import RadiusSession
        from stats.models import StatsUsersActiveSessions
        
        now = timezone.now()
        
        # Get count of active sessions grouped by username
        # Only include users with at least one active session
        from django.db.models import Count
        
        user_sessions = RadiusSession.objects.filter(
            status=RadiusSession.STATUS_ACTIVE
        ).values('username').annotate(
            session_count=Count('id')
        )
        
        # Create stats records for each user
        stats_records = []
        for user_stat in user_sessions:
            stats_records.append(
                StatsUsersActiveSessions(
                    timestamp=now,
                    username=user_stat['username'],
                    active_sessions=user_stat['session_count']
                )
            )
        
        if stats_records:
            StatsUsersActiveSessions.objects.bulk_create(stats_records)
            logger.debug(f"Stats: Saved active sessions for {len(stats_records)} users")
        else:
            logger.debug("Stats: No users with active sessions to record")
        
    except Exception as e:
        logger.error(f"Error collecting users active sessions: {e}")


def collect_users_total_traffic() -> None:
    """
    Collect and save per-user traffic stats.
    For each user, saves current traffic totals to stats.
    """
    try:
        from users.models import RadiusUser
        from stats.models import StatsUsersTotalTraffic
        
        now = timezone.now()
        
        # Get all users with traffic data
        users = RadiusUser.objects.filter(
            total_traffic__gt=0
        ).values('username', 'rx_traffic', 'tx_traffic', 'total_traffic')
        
        # Create stats records for each user
        stats_records = []
        for user in users:
            stats_records.append(
                StatsUsersTotalTraffic(
                    timestamp=now,
                    username=user['username'],
                    rx_traffic=user['rx_traffic'],
                    tx_traffic=user['tx_traffic'],
                    total_traffic=user['total_traffic']
                )
            )
        
        if stats_records:
            StatsUsersTotalTraffic.objects.bulk_create(stats_records)
            logger.debug(f"Stats: Saved traffic stats for {len(stats_records)} users")
        else:
            logger.debug("Stats: No users with traffic to record")
        
    except Exception as e:
        logger.error(f"Error collecting users total traffic: {e}")
