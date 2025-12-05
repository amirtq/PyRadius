"""
RADIUS Session Model

This module defines the RadiusSession model for tracking active and
historical VPN sessions for concurrent connection control.
"""

from django.db import models
from django.utils import timezone

class RadiusSession(models.Model):
    """
    Model representing a RADIUS/VPN session.
    Stores session data in SQLite database.
    """
    
    # Session status choices
    STATUS_ACTIVE = 'active'
    STATUS_STOPPED = 'stopped'
    
    STATUS_CHOICES = (
        (STATUS_ACTIVE, 'Active'),
        (STATUS_STOPPED, 'Stopped'),
    )
    
    # Terminate cause codes (RFC 2866)
    TERMINATE_CAUSE_USER_REQUEST = 1
    TERMINATE_CAUSE_LOST_CARRIER = 2
    TERMINATE_CAUSE_LOST_SERVICE = 3
    TERMINATE_CAUSE_IDLE_TIMEOUT = 4
    TERMINATE_CAUSE_SESSION_TIMEOUT = 5
    TERMINATE_CAUSE_ADMIN_RESET = 6
    TERMINATE_CAUSE_ADMIN_REBOOT = 7
    TERMINATE_CAUSE_PORT_ERROR = 8
    TERMINATE_CAUSE_NAS_ERROR = 9
    TERMINATE_CAUSE_NAS_REQUEST = 10
    TERMINATE_CAUSE_NAS_REBOOT = 11
    TERMINATE_CAUSE_PORT_UNNEEDED = 12
    TERMINATE_CAUSE_PORT_PREEMPTED = 13
    TERMINATE_CAUSE_PORT_SUSPENDED = 14
    TERMINATE_CAUSE_SERVICE_UNAVAILABLE = 15
    TERMINATE_CAUSE_CALLBACK = 16
    TERMINATE_CAUSE_USER_ERROR = 17
    TERMINATE_CAUSE_HOST_REQUEST = 18
    
    session_id = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Unique session identifier (Acct-Session-Id)"
    )
    username = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Username of the connected user"
    )
    nas_identifier = models.CharField(
        max_length=64,
        blank=True,
        default='',
        help_text="Identifier of the NAS"
    )
    nas_ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address of the NAS"
    )
    framed_ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="IP address assigned to the VPN client"
    )
    calling_station_id = models.CharField(
        max_length=64,
        blank=True,
        default='',
        help_text="Client identifier (MAC address or IP)"
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
        help_text="Current session status"
    )
    start_time = models.DateTimeField(
        default=timezone.now,
        help_text="When the session started"
    )
    stop_time = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the session ended"
    )
    session_time = models.PositiveIntegerField(
        default=0,
        help_text="Total session duration in seconds"
    )
    input_octets = models.BigIntegerField(
        default=0,
        help_text="Bytes received from client"
    )
    output_octets = models.BigIntegerField(
        default=0,
        help_text="Bytes sent to client"
    )
    input_packets = models.BigIntegerField(
        default=0,
        help_text="Packets received from client"
    )
    output_packets = models.BigIntegerField(
        default=0,
        help_text="Packets sent to client"
    )
    terminate_cause = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Reason for session termination (RFC 2866)"
    )
    
    class Meta:
        db_table = 'radius_sessions'
        verbose_name = 'RADIUS Session'
        verbose_name_plural = 'RADIUS Sessions'
        ordering = ['-start_time']
        unique_together = [['session_id', 'nas_ip_address']]
        indexes = [
            models.Index(fields=['username', 'status']),
            models.Index(fields=['nas_ip_address', 'status']),
        ]

    def __str__(self):
        return f"{self.username}@{self.nas_identifier} ({self.session_id})"
    
    def stop_session(self, 
                     terminate_cause: int | None = None,
                     session_time: int | None = None,
                     input_octets: int | None = None,
                     output_octets: int | None = None,
                     input_packets: int | None = None,
                     output_packets: int | None = None) -> None:
        """
        Mark the session as stopped and update statistics.
        """
        self.status = self.STATUS_STOPPED
        self.stop_time = timezone.now()
        
        if terminate_cause is not None:
            self.terminate_cause = terminate_cause
        if session_time is not None:
            self.session_time = session_time
        if input_octets is not None:
            self.input_octets = input_octets
        if output_octets is not None:
            self.output_octets = output_octets
        if input_packets is not None:
            self.input_packets = input_packets
        if output_packets is not None:
            self.output_packets = output_packets
        
        self.save()

        # Update user session counts
        try:
            from users.models import RadiusUser
            user = RadiusUser.objects.get(username=self.username)
            user.update_session_counts()
        except Exception:
            # Ignore if user not found or error logic
            pass
    
    def update_statistics(self,
                          session_time: int | None = None,
                          input_octets: int | None = None,
                          output_octets: int | None = None,
                          input_packets: int | None = None,
                          output_packets: int | None = None) -> None:
        """
        Update session statistics (from Interim-Update).
        """
        if session_time is not None:
            self.session_time = session_time
        if input_octets is not None:
            self.input_octets = input_octets
        if output_octets is not None:
            self.output_octets = output_octets
        if input_packets is not None:
            self.input_packets = input_packets
        if output_packets is not None:
            self.output_packets = output_packets
        
        self.save()
    
    @classmethod
    def create_session(cls,
                       session_id: str,
                       username: str,
                       nas_identifier: str = '',
                       nas_ip_address: str | None = None,
                       framed_ip_address: str | None = None,
                       calling_station_id: str = '') -> 'RadiusSession':
        """
        Create a new active session.
        """
        # Cleanup old inactive sessions before creating a new one
        cls.cleanup_inactive_sessions()

        session = cls(
            session_id=session_id,
            username=username,
            nas_identifier=nas_identifier,
            nas_ip_address=nas_ip_address,
            framed_ip_address=framed_ip_address,
            calling_station_id=calling_station_id,
            status=cls.STATUS_ACTIVE,
            start_time=timezone.now()
        )
        session.save()
        
        # Update user session counts
        try:
            from users.models import RadiusUser
            user = RadiusUser.objects.get(username=username)
            user.update_session_counts()
        except Exception:
            pass
            
        return session
    
    @classmethod
    def find_session(cls, session_id: str, nas_ip_address: str | None = None) -> 'RadiusSession | None':
        """
        Find an existing session by session ID.
        """
        qs = cls.objects.filter(session_id=session_id)
        if nas_ip_address:
            qs = qs.filter(nas_ip_address=nas_ip_address)
        return qs.first()
    
    @classmethod
    def get_active_sessions_for_user(cls, username: str) -> list:
        """
        Get all active sessions for a user.
        """
        return list(cls.objects.filter(username=username, status=cls.STATUS_ACTIVE))
    
    @classmethod
    def count_active_sessions_for_user(cls, username: str) -> int:
        """
        Count active sessions for a user.
        """
        return cls.objects.filter(username=username, status=cls.STATUS_ACTIVE).count()
    
    @classmethod
    def cleanup_inactive_sessions(cls) -> None:
        """
        Keep only the last N inactive sessions and delete older ones.
        N is configured via MAX_INACTIVE_SESSIONS in RADIUS_CONFIG.
        """
        from django.conf import settings
        
        limit = settings.RADIUS_CONFIG.get('MAX_INACTIVE_SESSIONS', 100)
        
        # Get all stopped sessions ordered by stop_time desc (newest first)
        qs = cls.objects.filter(status=cls.STATUS_STOPPED).order_by('-stop_time')
        
        if qs.count() > limit:
            # We have more than the limit.
            # Get the IDs of the top 'limit' sessions to keep.
            keep_ids = list(qs[:limit].values_list('id', flat=True))
            
            # Delete sessions that are NOT in the keep list
            cls.objects.filter(status=cls.STATUS_STOPPED).exclude(id__in=keep_ids).delete()

    @classmethod
    def cleanup_stale_sessions(cls, max_age_hours: int = 24) -> int:
        """
        Clean up stale sessions that have been active for too long.
        """
        cutoff_time = timezone.now() - timezone.timedelta(hours=max_age_hours)
        
        stale_sessions = cls.objects.filter(
            status=cls.STATUS_ACTIVE,
            start_time__lt=cutoff_time
        )
        
        count = stale_sessions.count()
        if count > 0:
            # Get list of affected users before update
            affected_users = set(stale_sessions.values_list('username', flat=True))
            
            stale_sessions.update(
                status=cls.STATUS_STOPPED,
                stop_time=timezone.now(),
                terminate_cause=cls.TERMINATE_CAUSE_SESSION_TIMEOUT
            )
            
            # Update counts for affected users
            from users.models import RadiusUser
            for username in affected_users:
                try:
                    user = RadiusUser.objects.get(username=username)
                    user.update_session_counts()
                except RadiusUser.DoesNotExist:
                    pass
            
        return count
