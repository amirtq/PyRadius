"""
NAS Client Model

This module defines the NASClient model for storing Network Access Server
(NAS) configurations, including shared secrets for RADIUS authentication.
"""

import threading
import time
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
import ipaddress


# Simple in-memory cache for NAS clients with TTL
# Thread-safe implementation using threading.Lock
class NASCache:
    """Thread-safe in-memory cache for NAS clients."""
    
    def __init__(self, default_ttl: int = 300):
        """Initialize cache with default TTL in seconds."""
        self._cache: dict = {}
        self._lock = threading.Lock()
        self._default_ttl = default_ttl
    
    def get(self, key: str):
        """Get item from cache. Returns None if not found or expired."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.time() > expires_at:
                # Expired, remove from cache
                del self._cache[key]
                return None
            return value
    
    def set(self, key: str, value, ttl: int | None = None):
        """Set item in cache with optional TTL override."""
        ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.time() + ttl
        with self._lock:
            self._cache[key] = (value, expires_at)
    
    def clear(self):
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
    
    def invalidate(self, key: str):
        """Remove a specific key from cache."""
        with self._lock:
            self._cache.pop(key, None)


# Global NAS cache instance (300 seconds = 5 minutes TTL)
_nas_cache = NASCache(default_ttl=300)


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
        Get a NAS client by its IP address (with caching).
        
        Args:
            ip_address: The IP address to look up
            
        Returns:
            NASClient instance or None if not found
        """
        cache_key = f"nas_ip:{ip_address}"
        
        # Try cache first
        cached = _nas_cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Query database
        nas = cls.objects.filter(ip_address=ip_address, is_active=True).first()
        
        # Cache result (even None to avoid repeated lookups for invalid IPs)
        _nas_cache.set(cache_key, nas)
        return nas
    
    @classmethod
    def get_by_identifier(cls, identifier: str) -> 'NASClient | None':
        """
        Get a NAS client by its identifier (with caching).
        
        Args:
            identifier: The NAS identifier to look up
            
        Returns:
            NASClient instance or None if not found
        """
        cache_key = f"nas_id:{identifier}"
        
        # Try cache first
        cached = _nas_cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Query database
        nas = cls.objects.filter(identifier=identifier, is_active=True).first()
        
        # Cache result
        _nas_cache.set(cache_key, nas)
        return nas

    @classmethod
    def get_best_match(cls, ip_address: str, identifier: str | None = None) -> 'NASClient | None':
        """
        Find the best matching NAS client given an IP and optional identifier (with caching).
        
        Args:
            ip_address: Source IP address
            identifier: NAS-Identifier attribute (optional)
            
        Returns:
            Best matching NASClient or None
        """
        # Create cache key based on both parameters
        cache_key = f"nas_match:{ip_address}:{identifier or ''}"
        
        # Try cache first
        cached = _nas_cache.get(cache_key)
        if cached is not None:
            # Handle cached None (stored as False to distinguish from cache miss)
            return cached if cached is not False else None
        
        # Get all active clients for this IP
        qs = cls.objects.filter(ip_address=ip_address, is_active=True)
        
        if not qs.exists():
            _nas_cache.set(cache_key, False)  # Cache "not found"
            return None
            
        # If identifier provided, try to find exact match
        if identifier:
            match = qs.filter(identifier=identifier).first()
            if match:
                _nas_cache.set(cache_key, match)
                return match
            # If no match for identifier, we return None (strict matching)
            # This handles case where we have clients A and B on same IP,
            # and request comes for C. We shouldn't authenticate as A or B.
            _nas_cache.set(cache_key, False)  # Cache "not found"
            return None
             
        # If no identifier provided, return the first one (fallback)
        nas = qs.first()
        _nas_cache.set(cache_key, nas if nas else False)
        return nas
    
    @classmethod
    def find_nas(cls, ip_address: str | None = None, identifier: str | None = None) -> 'NASClient | None':
        """
        Find a NAS client by IP address or identifier (with caching).
        
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
    
    @classmethod
    def clear_cache(cls):
        """Clear the NAS cache. Call this when NAS configuration changes."""
        _nas_cache.clear()
    
    def save(self, *args, **kwargs):
        """Override save to invalidate cache when NAS is modified."""
        super().save(*args, **kwargs)
        # Clear cache when any NAS is modified
        _nas_cache.clear()
    
    def delete(self, *args, **kwargs):
        """Override delete to invalidate cache when NAS is removed."""
        super().delete(*args, **kwargs)
        # Clear cache when any NAS is deleted
        _nas_cache.clear()
    
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
