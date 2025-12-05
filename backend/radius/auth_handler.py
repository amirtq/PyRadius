"""
RADIUS Authentication Handler

This module handles Access-Request packets from NAS clients,
authenticating users against the database.
"""

import logging
from typing import Tuple, Optional

from django.conf import settings
from pyrad import packet
from pyrad.dictionary import Dictionary

logger = logging.getLogger(__name__)


class AuthenticationHandler:
    """
    Handles RADIUS authentication requests.
    
    This class processes Access-Request packets, validates user credentials,
    checks account status, and enforces concurrent session limits.
    """
    
    def __init__(self, dictionary: Dictionary):
        """
        Initialize the authentication handler.
        
        Args:
            dictionary: RADIUS dictionary for attribute parsing
        """
        self.dictionary = dictionary
    
    def handle_auth_request(self, pkt: packet.AuthPacket, 
                            client_address: Tuple[str, int]) -> packet.AuthPacket:
        """
        Handle an Access-Request packet.
        
        Args:
            pkt: The incoming Access-Request packet
            client_address: Tuple of (ip, port) of the client
            
        Returns:
            Access-Accept or Access-Reject packet
        """
        # Import here to avoid circular imports and ensure Django is initialized
        from users.models import RadiusUser
        from nas.models import NASClient
        
        # Extract attributes from the packet
        username = self._get_attribute(pkt, 'User-Name')
        password = self._get_user_password(pkt)
        nas_identifier = self._get_attribute(pkt, 'NAS-Identifier')
        nas_ip = self._get_attribute(pkt, 'NAS-IP-Address') or client_address[0]
        calling_station_id = self._get_attribute(pkt, 'Calling-Station-Id')
        
        logger.info(f"Auth request: user={username}, nas={nas_identifier}, "
                   f"nas_ip={nas_ip}, client={calling_station_id}")
        
        # Validate required attributes
        if not username:
            logger.warning("Auth request missing User-Name attribute")
            return self._create_reject_response(pkt, "Missing username")
        
        if not password:
            logger.warning(f"Auth request for {username} missing password")
            return self._create_reject_response(pkt, "Missing password")
        
        # Verify NAS client
        nas_client = NASClient.find_nas(ip_address=nas_ip, identifier=nas_identifier)
        if not nas_client:
            logger.warning(f"Unknown NAS: ip={nas_ip}, identifier={nas_identifier}")
            return self._create_reject_response(pkt, "Unknown NAS client")
        
        # Look up user
        try:
            user = RadiusUser.objects.get(username=username)
        except RadiusUser.DoesNotExist:
            logger.warning(f"User not found: {username}")
            return self._create_reject_response(pkt, "Invalid credentials")
        
        # Verify password
        if not user.check_password(password):
            logger.warning(f"Invalid password for user: {username}")
            return self._create_reject_response(pkt, "Invalid credentials")
        
        # Check if user can authenticate (active, not expired)
        can_auth, reason = user.can_authenticate()
        if not can_auth:
            logger.warning(f"User {username} cannot authenticate: {reason}")
            return self._create_reject_response(pkt, reason)
        
        # Check concurrent session limit
        can_create, reason = user.can_create_session()
        if not can_create:
            logger.warning(f"User {username} cannot create session: {reason}")
            return self._create_reject_response(pkt, reason)
        
        # Authentication successful
        logger.info(f"Auth success for user: {username}")
        return self._create_accept_response(pkt)
    
    def _get_attribute(self, pkt: packet.AuthPacket, attr_name: str) -> Optional[str]:
        """
        Get an attribute value from a packet.
        
        Args:
            pkt: The RADIUS packet
            attr_name: Name of the attribute to get
            
        Returns:
            The attribute value as string, or None if not found
        """
        try:
            values = pkt.get(attr_name)
            if values:
                value = values[0]
                if isinstance(value, bytes):
                    return value.decode('utf-8')
                return str(value)
        except Exception as e:
            logger.debug(f"Error getting attribute {attr_name}: {e}")
        return None
    
    def _get_user_password(self, pkt: packet.AuthPacket) -> Optional[str]:
        """
        Decrypt and get the User-Password from the packet.
        
        Args:
            pkt: The RADIUS packet
            
        Returns:
            The decrypted password, or None if not available
        """
        try:
            # pyrad handles password decryption internally
            user_password = pkt.get('User-Password')
            if not user_password:
                return None
            password = pkt.PwDecrypt(user_password[0])
            if isinstance(password, bytes):
                return password.decode('utf-8')
            return password
        except Exception as e:
            logger.debug(f"Error decrypting password: {e}")
            return None
    
    def _create_accept_response(self, request: packet.AuthPacket) -> packet.AuthPacket:
        """
        Create an Access-Accept response packet.
        
        Args:
            request: The original request packet
            
        Returns:
            Access-Accept packet
        """
        reply = request.CreateReply()
        reply['Reply-Message'] = 'Authentication successful'
        
        # Add Service-Type attribute
        reply['Service-Type'] = 'Framed'
        reply['Framed-Protocol'] = 'PPP'
        
        # Add Acct-Interim-Interval attribute
        # Default to 600s (10m) if not configured
        interim_interval = settings.RADIUS_CONFIG.get('ACCT_INTERIM_INTERVAL', 600)
        reply['Acct-Interim-Interval'] = interim_interval
        
        return reply
    
    def _create_reject_response(self, request: packet.AuthPacket, 
                                 reason: str) -> packet.AuthPacket:
        """
        Create an Access-Reject response packet.
        
        Args:
            request: The original request packet
            reason: Reason for rejection
            
        Returns:
            Access-Reject packet
        """
        reply = request.CreateReply()
        reply.code = packet.AccessReject
        reply['Reply-Message'] = reason
        return reply
