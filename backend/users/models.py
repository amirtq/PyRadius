"""
RADIUS User Model

This module defines the RadiusUser model for storing user credentials
and settings for RADIUS authentication.
"""

from django.db import models
from django.utils import timezone
import bcrypt

class RadiusUser(models.Model):
    """
    Model representing a RADIUS user for VPN authentication.
    Stores user data in SQLite database.
    """
    
    username = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Unique username for authentication"
    )
    password_hash = models.CharField(
        max_length=128,
        help_text="Bcrypt hashed password"
    )
    max_concurrent_sessions = models.PositiveIntegerField(
        default=1,
        help_text="Maximum number of concurrent VPN sessions allowed"
    )
    expiration_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Optional expiration date for the account"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the account is active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(
        blank=True,
        default='',
        help_text="Optional notes about the user"
    )
    
    # Traffic Accounting
    rx_traffic = models.BigIntegerField(
        default=0,
        help_text="Total bytes received (download)"
    )
    tx_traffic = models.BigIntegerField(
        default=0,
        help_text="Total bytes sent (upload)"
    )
    total_traffic = models.BigIntegerField(
        default=0,
        help_text="Total traffic (rx + tx)"
    )

    allowed_traffic = models.BigIntegerField(
        null=True,
        blank=True,
        help_text="Maximum allowed traffic in bytes (NULL for unlimited)"
    )

    current_sessions = models.PositiveIntegerField(
        default=0,
        help_text="Current number of active sessions"
    )
    remaining_sessions = models.IntegerField(
        default=1,
        help_text="Remaining allowed sessions"
    )

    class Meta:
        db_table = 'radius_users'
        verbose_name = 'RADIUS User'
        verbose_name_plural = 'RADIUS Users'
        ordering = ['username']

    def __str__(self):
        return self.username
    
    def set_password(self, plain_password: str, use_cleartext: bool = False) -> None:
        """
        Hash and set the user's password using bcrypt, or store as cleartext.
        """
        if use_cleartext:
            self.password_hash = f"ctp:{plain_password}"
        else:
            salt = bcrypt.gensalt()
            self.password_hash = bcrypt.hashpw(
                plain_password.encode('utf-8'),
                salt
            ).decode('utf-8')
    
    def check_password(self, plain_password: str) -> bool:
        """
        Verify a plain text password against the stored hash.
        """
        if not self.password_hash:
            return False
        
        if self.password_hash.startswith('ctp:'):
            return self.password_hash.removeprefix('ctp:') == plain_password

        return bcrypt.checkpw(
            plain_password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )
    
    def is_expired(self) -> bool:
        """
        Check if the user account has expired.
        """
        if self.expiration_date is None:
            return False
        return timezone.now() > self.expiration_date
    
    def can_authenticate(self) -> tuple[bool, str]:
        """
        Check if the user can authenticate.
        """
        if not self.is_active:
            return False, "Account is disabled"
        if self.is_expired():
            return False, "Account has expired"
        if self.allowed_traffic is not None and self.total_traffic >= self.allowed_traffic:
            return False, "Traffic limit reached"
        return True, "OK"
    
    def get_active_session_count(self) -> int:
        """
        Get the number of currently active sessions for this user.
        """
        return self.current_sessions
    
    def update_session_counts(self) -> None:
        """
        Recalculate and save session counts.
        """
        if not self.username:
            return
            
        from sessions.models import RadiusSession
        self.current_sessions = RadiusSession.count_active_sessions_for_user(self.username)
        self.remaining_sessions = self.max_concurrent_sessions - self.current_sessions
        # Avoid recursion by calling super().save() or just save with update_fields?
        # save() override handles logic too, but explicit calculation here is safer
        # against race conditions if we used F() expressions (which we aren't yet).
        self.save()

    def save(self, *args, **kwargs):
        """
        Override save to update remaining sessions count.
        """
        self.remaining_sessions = self.max_concurrent_sessions - self.current_sessions
        super().save(*args, **kwargs)

    def can_create_session(self) -> tuple[bool, str]:
        """
        Check if the user can create a new session.
        """
        can_auth, reason = self.can_authenticate()
        if not can_auth:
            return False, reason
        
        active_sessions = self.get_active_session_count()
        if active_sessions >= self.max_concurrent_sessions:
            return False, f"Maximum concurrent sessions ({self.max_concurrent_sessions}) reached"
        
        return True, "OK"
