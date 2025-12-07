"""
Statistics Models

This module defines models for storing historical statistics data:
- Server-wide active sessions over time
- Server-wide total traffic over time
- Per-user active sessions over time
- Per-user total traffic over time
"""

from django.db import models
from django.utils import timezone

# Constants for help text to avoid duplication
HELP_TEXT_TIMESTAMP = "When this stat was recorded"
HELP_TEXT_USERNAME = "Username of the user"


class StatsServerActiveSessions(models.Model):
    """
    Model for storing server-wide active session count over time.
    Records are saved at configurable intervals.
    """
    
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text=HELP_TEXT_TIMESTAMP
    )
    active_sessions = models.PositiveIntegerField(
        default=0,
        help_text="Total number of active sessions at this time"
    )
    
    class Meta:
        db_table = 'stats_server_active_sessions'
        verbose_name = 'Server Active Sessions Stat'
        verbose_name_plural = 'Server Active Sessions Stats'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.timestamp.isoformat()}: {self.active_sessions} sessions"


class StatsServerTotalTraffic(models.Model):
    """
    Model for storing server-wide total traffic over time.
    Records are saved at configurable intervals.
    """
    
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text=HELP_TEXT_TIMESTAMP
    )
    total_rx = models.BigIntegerField(
        default=0,
        help_text="Total bytes received (download) across all users"
    )
    total_tx = models.BigIntegerField(
        default=0,
        help_text="Total bytes sent (upload) across all users"
    )
    total_traffic = models.BigIntegerField(
        default=0,
        help_text="Total traffic (rx + tx) across all users"
    )
    
    class Meta:
        db_table = 'stats_server_total_traffic'
        verbose_name = 'Server Total Traffic Stat'
        verbose_name_plural = 'Server Total Traffic Stats'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.timestamp.isoformat()}: {self.total_traffic} bytes"


class StatsUsersActiveSessions(models.Model):
    """
    Model for storing per-user active session count over time.
    Records are saved at configurable intervals per user.
    """
    
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text=HELP_TEXT_TIMESTAMP
    )
    username = models.CharField(
        max_length=64,
        db_index=True,
        help_text=HELP_TEXT_USERNAME
    )
    active_sessions = models.PositiveIntegerField(
        default=0,
        help_text="Number of active sessions for this user at this time"
    )
    
    class Meta:
        db_table = 'stats_users_active_sessions'
        verbose_name = 'User Active Sessions Stat'
        verbose_name_plural = 'User Active Sessions Stats'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['username', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.timestamp.isoformat()}: {self.username} - {self.active_sessions} sessions"


class StatsUsersTotalTraffic(models.Model):
    """
    Model for storing per-user traffic over time.
    Records are saved at configurable intervals per user.
    """
    
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text=HELP_TEXT_TIMESTAMP
    )
    username = models.CharField(
        max_length=64,
        db_index=True,
        help_text=HELP_TEXT_USERNAME
    )
    rx_traffic = models.BigIntegerField(
        default=0,
        help_text="Total bytes received (download) by this user"
    )
    tx_traffic = models.BigIntegerField(
        default=0,
        help_text="Total bytes sent (upload) by this user"
    )
    total_traffic = models.BigIntegerField(
        default=0,
        help_text="Total traffic (rx + tx) for this user"
    )
    
    class Meta:
        db_table = 'stats_users_total_traffic'
        verbose_name = 'User Total Traffic Stat'
        verbose_name_plural = 'User Total Traffic Stats'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['username', '-timestamp']),
            models.Index(fields=['-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.timestamp.isoformat()}: {self.username} - {self.total_traffic} bytes"
