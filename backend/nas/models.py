"""
NAS Client Model

This module defines the NASClient model for storing Network Access Server
(NAS) configurations, including shared secrets for RADIUS authentication.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import ipaddress


class NASClient(models.Model):
    """
    Model representing a Network Access Server (NAS) client.
    
    A NAS client is typically an OpenVPN server that sends RADIUS
    authentication and accounting requests.
    
    Attributes:
        identifier: Unique identifier for the NAS (e.g., "openvpn")
        ip_address: IP address of the NAS
        shared_secret: Shared secret for RADIUS packet authentication
        auth_port: Authentication port (default 1812)
        acct_port: Accounting port (default 1813)
        is_active: Whether the NAS is active
        description: Optional description of the NAS
        created_at: Timestamp when the NAS was added
        updated_at: Timestamp when the NAS was last updated
    """
    
    identifier = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Unique identifier for the NAS (matches NAS-Identifier attribute)"
    )
    ip_address = models.GenericIPAddressField(
        help_text="IP address of the NAS"
    )
    shared_secret = models.CharField(
        max_length=128,
        help_text="Shared secret for RADIUS authentication"
    )
    auth_port = models.PositiveIntegerField(
        default=1812,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
        help_text="Authentication port"
    )
    acct_port = models.PositiveIntegerField(
        default=1813,
        validators=[MinValueValidator(1), MaxValueValidator(65535)],
        help_text="Accounting port"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the NAS is active"
    )
    description = models.TextField(
        blank=True,
        default='',
        help_text="Optional description of the NAS"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'radius_nas_clients'
        verbose_name = 'NAS Client'
        verbose_name_plural = 'NAS Clients'
        ordering = ['identifier']
        # Ensure unique combination of IP and identifier
        unique_together = [['identifier', 'ip_address']]
    
    def __str__(self):
        return f"{self.identifier} ({self.ip_address})"
    
    def get_secret_bytes(self) -> bytes:
        """
        Get the shared secret as bytes for RADIUS operations.
        
        Returns:
            The shared secret encoded as bytes
        """
        return self.shared_secret.encode('utf-8')
    
    @classmethod
    def get_by_ip(cls, ip_address: str) -> 'NASClient | None':
        """
        Get a NAS client by its IP address.
        
        Args:
            ip_address: The IP address to look up
            
        Returns:
            NASClient instance or None if not found
        """
        try:
            return cls.objects.get(ip_address=ip_address, is_active=True)
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def get_by_identifier(cls, identifier: str) -> 'NASClient | None':
        """
        Get a NAS client by its identifier.
        
        Args:
            identifier: The NAS identifier to look up
            
        Returns:
            NASClient instance or None if not found
        """
        try:
            return cls.objects.get(identifier=identifier, is_active=True)
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def find_nas(cls, ip_address: str | None = None, identifier: str | None = None) -> 'NASClient | None':
        """
        Find a NAS client by IP address or identifier.
        
        Tries to find by IP first, then by identifier.
        
        Args:
            ip_address: Optional IP address to look up
            identifier: Optional NAS identifier to look up
            
        Returns:
            NASClient instance or None if not found
        """
        if ip_address:
            nas = cls.get_by_ip(ip_address)
            if nas:
                return nas
        
        if identifier:
            nas = cls.get_by_identifier(identifier)
            if nas:
                return nas
        
        return None
    
    def is_ip_allowed(self, source_ip: str) -> bool:
        """
        Check if a source IP is allowed to use this NAS configuration.
        
        For now, this checks if the source IP matches the configured IP.
        Future versions could support IP ranges.
        
        Args:
            source_ip: The source IP to check
            
        Returns:
            True if the IP is allowed, False otherwise
        """
        try:
            configured_ip = ipaddress.ip_address(self.ip_address)
            source = ipaddress.ip_address(source_ip)
            return configured_ip == source
        except ValueError:
            return False
