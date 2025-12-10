"""
RADIUS Accounting Handler

This module handles Accounting-Request packets from NAS clients,
managing session start, stop, and interim updates.
"""

import logging
from typing import Tuple, Optional

from pyrad import packet
from pyrad.dictionary import Dictionary

logger = logging.getLogger(__name__)

# Acct-Status-Type values (RFC 2866)
ACCT_STATUS_START = 1
ACCT_STATUS_STOP = 2
ACCT_STATUS_INTERIM_UPDATE = 3
ACCT_STATUS_ACCOUNTING_ON = 7
ACCT_STATUS_ACCOUNTING_OFF = 8

# Mapping for string values returned by pyrad
ACCT_STATUS_MAP = {
    'Start': ACCT_STATUS_START,
    'Stop': ACCT_STATUS_STOP,
    'Interim-Update': ACCT_STATUS_INTERIM_UPDATE,
    'Accounting-On': ACCT_STATUS_ACCOUNTING_ON,
    'Accounting-Off': ACCT_STATUS_ACCOUNTING_OFF,
}

ACCT_TERMINATE_CAUSE_MAP = {
    'User-Request': 1,
    'Lost-Carrier': 2,
    'Lost-Service': 3,
    'Idle-Timeout': 4,
    'Session-Timeout': 5,
    'Admin-Reset': 6,
    'Admin-Reboot': 7,
    'Port-Error': 8,
    'NAS-Error': 9,
    'NAS-Request': 10,
    'NAS-Reboot': 11,
    'Port-Unneeded': 12,
    'Port-Preempted': 13,
    'Port-Suspended': 14,
    'Service-Unavailable': 15,
    'Callback': 16,
    'User-Error': 17,
    'Host-Request': 18,
}


class AccountingHandler:
    """
    Handles RADIUS accounting requests.
    
    This class processes Accounting-Request packets to track VPN session
    lifecycle (start, stop, interim updates) and maintain concurrent
    connection counts.
    """
    
    def __init__(self, dictionary: Dictionary):
        """
        Initialize the accounting handler.
        
        Args:
            dictionary: RADIUS dictionary for attribute parsing
        """
        self.dictionary = dictionary
    
    def handle_acct_request(self, pkt: packet.AcctPacket,
                            client_address: Tuple[str, int]) -> packet.AcctPacket:
        """
        Handle an Accounting-Request packet.
        
        Args:
            pkt: The incoming Accounting-Request packet
            client_address: Tuple of (ip, port) of the client
            
        Returns:
            Accounting-Response packet
        """
        # Note: Dead session cleanup is now handled by the scheduler
        # (scheduler.jobs.cleanup.cleanup_dead_sessions) to avoid blocking

        # Extract common attributes
        acct_status_type = self._get_int_attribute(pkt, 'Acct-Status-Type', ACCT_STATUS_MAP)
        session_id = self._get_attribute(pkt, 'Acct-Session-Id')
        username = self._get_attribute(pkt, 'User-Name')
        nas_identifier = self._get_attribute(pkt, 'NAS-Identifier')
        nas_ip = self._get_attribute(pkt, 'NAS-IP-Address') or client_address[0]
        
        logger.info(f"Acct request: type={acct_status_type}, user={username}, "
                   f"session={session_id}, nas={nas_identifier}")
        
        if acct_status_type == ACCT_STATUS_START:
            self._handle_start(pkt, username, session_id, nas_identifier, nas_ip)
        elif acct_status_type == ACCT_STATUS_STOP:
            self._handle_stop(pkt, username, session_id, nas_ip)
        elif acct_status_type == ACCT_STATUS_INTERIM_UPDATE:
            self._handle_interim_update(pkt, session_id, nas_ip)
        elif acct_status_type == ACCT_STATUS_ACCOUNTING_ON:
            self._handle_accounting_on(nas_ip)
        elif acct_status_type == ACCT_STATUS_ACCOUNTING_OFF:
            self._handle_accounting_off(nas_ip)
        else:
            logger.warning(f"Unknown Acct-Status-Type: {acct_status_type}")
        
        # Always respond with Accounting-Response
        return self._create_response(pkt)
    
    def _handle_start(self, pkt: packet.AcctPacket, username: Optional[str], 
                      session_id: Optional[str], nas_identifier: Optional[str], nas_ip: str) -> None:
        """
        Handle Accounting-Start request.
        
        Queues a new session record for the user in the session buffer.
        The session will be written to the database during the next buffer flush.
        
        Args:
            pkt: The accounting packet
            username: Username
            session_id: Session identifier
            nas_identifier: NAS identifier
            nas_ip: NAS IP address
        """
        from sessions.buffer import get_session_buffer
        
        if not username or not session_id:
            logger.warning("Acct-Start missing required attributes")
            return
        
        # Get optional attributes
        framed_ip = self._get_attribute(pkt, 'Framed-IP-Address')
        calling_station_id = self._get_attribute(pkt, 'Calling-Station-Id') or ''
        
        # Check if session already exists in buffer
        buffer = get_session_buffer()
        if buffer.is_session_pending(session_id, nas_ip):
            logger.warning(f"Session {session_id} already pending in buffer, ignoring start")
            return
        
        # Check if session already exists in database
        from sessions.models import RadiusSession
        existing = RadiusSession.find_session(session_id, nas_ip)
        if existing:
            logger.warning(f"Session {session_id} already exists in database, ignoring start")
            return
        
        # Queue the session start in the buffer
        # Note: Stale session cleanup is handled during buffer flush
        try:
            buffer.add_start(
                session_id=session_id,
                username=username,
                nas_ip_address=nas_ip,
                nas_identifier=nas_identifier or '',
                framed_ip_address=framed_ip,
                calling_station_id=calling_station_id
            )
            logger.info(f"Session queued: {session_id} for user {username}")
        except Exception as e:
            logger.error(f"Error queuing session: {e}")
    
    def _handle_stop(self, pkt: packet.AcctPacket, username: Optional[str],
                     session_id: Optional[str], nas_ip: str) -> None:
        """
        Handle Accounting-Stop request.
        
        Queues the session stop in the buffer for batch processing.
        
        Args:
            pkt: The accounting packet
            username: Username
            session_id: Session identifier
            nas_ip: NAS IP address
        """
        from sessions.buffer import get_session_buffer
        
        if not session_id:
            logger.warning("Acct-Stop missing session ID")
            return
        
        if not username:
            username = ''
        
        # Get statistics from packet
        session_time = self._get_int_attribute(pkt, 'Acct-Session-Time')
        input_octets = self._get_int_attribute(pkt, 'Acct-Input-Octets')
        output_octets = self._get_int_attribute(pkt, 'Acct-Output-Octets')
        input_packets = self._get_int_attribute(pkt, 'Acct-Input-Packets')
        output_packets = self._get_int_attribute(pkt, 'Acct-Output-Packets')
        terminate_cause = self._get_int_attribute(pkt, 'Acct-Terminate-Cause', ACCT_TERMINATE_CAUSE_MAP)
        
        # Queue the session stop in the buffer
        try:
            buffer = get_session_buffer()
            buffer.add_stop(
                session_id=session_id,
                nas_ip_address=nas_ip,
                username=username,
                terminate_cause=terminate_cause,
                session_time=session_time,
                input_octets=input_octets,
                output_octets=output_octets,
                input_packets=input_packets,
                output_packets=output_packets
            )
            logger.info(f"Session stop queued: {session_id} for user {username}, "
                       f"duration={session_time}s, in={input_octets}B, out={output_octets}B")
        except Exception as e:
            logger.error(f"Error queuing session stop: {e}")
    
    def _handle_interim_update(self, pkt: packet.AcctPacket,
                               session_id: Optional[str], nas_ip: str) -> None:
        """
        Handle Accounting-Interim-Update request.
        
        Queues session statistics update in the buffer for batch processing.
        
        Args:
            pkt: The accounting packet
            session_id: Session identifier
            nas_ip: NAS IP address
        """
        from sessions.buffer import get_session_buffer
        
        if not session_id:
            logger.warning("Acct-Interim-Update missing session ID")
            return
        
        # Get username from packet for buffer tracking
        username = self._get_attribute(pkt, 'User-Name') or ''
        
        # Get statistics from packet
        session_time = self._get_int_attribute(pkt, 'Acct-Session-Time')
        input_octets = self._get_int_attribute(pkt, 'Acct-Input-Octets')
        output_octets = self._get_int_attribute(pkt, 'Acct-Output-Octets')
        input_packets = self._get_int_attribute(pkt, 'Acct-Input-Packets')
        output_packets = self._get_int_attribute(pkt, 'Acct-Output-Packets')
        
        # Queue the session update in the buffer
        try:
            buffer = get_session_buffer()
            buffer.add_update(
                session_id=session_id,
                nas_ip_address=nas_ip,
                username=username,
                session_time=session_time,
                input_octets=input_octets,
                output_octets=output_octets,
                input_packets=input_packets,
                output_packets=output_packets
            )
            logger.debug(f"Session update queued: {session_id}")
        except Exception as e:
            logger.error(f"Error queuing session update: {e}")
    
    def _handle_accounting_on(self, nas_ip: str) -> None:
        """
        Handle Accounting-On request (NAS restart).
        
        This typically indicates that the NAS has restarted.
        We should clean up any stale sessions from this NAS.
        
        Args:
            nas_ip: NAS IP address
        """
        from sessions.models import RadiusSession
        
        logger.info(f"Accounting-On from NAS {nas_ip}, cleaning stale sessions")
        
        # Mark all active sessions from this NAS as stopped
        try:
            sessions = RadiusSession.objects.filter(
                nas_ip_address=nas_ip,
                status=RadiusSession.STATUS_ACTIVE
            )
            stale_count = 0
            for session in sessions:
                session.stop_session(
                    terminate_cause=RadiusSession.TERMINATE_CAUSE_NAS_REBOOT
                )
                stale_count += 1
                
            if stale_count:
                logger.info(f"Cleaned up {stale_count} stale sessions from NAS {nas_ip}")
        except Exception as e:
            logger.error(f"Error cleaning stale sessions: {e}")
    
    def _handle_accounting_off(self, nas_ip: str) -> None:
        """
        Handle Accounting-Off request (NAS shutdown).
        
        This typically indicates that the NAS is shutting down.
        
        Args:
            nas_ip: NAS IP address
        """
        from sessions.models import RadiusSession
        
        logger.info(f"Accounting-Off from NAS {nas_ip}")
        
        # Mark all active sessions from this NAS as stopped
        try:
            sessions = RadiusSession.objects.filter(
                nas_ip_address=nas_ip,
                status=RadiusSession.STATUS_ACTIVE
            )
            count = 0
            for session in sessions:
                session.stop_session(
                    terminate_cause=RadiusSession.TERMINATE_CAUSE_NAS_REQUEST
                )
                count += 1
                
            if count:
                logger.info(f"Stopped {count} sessions due to NAS shutdown")
        except Exception as e:
            logger.error(f"Error stopping sessions: {e}")
    
    def _get_attribute(self, pkt: packet.AcctPacket, attr_name: str) -> Optional[str]:
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
    
    def _resolve_int_value(self, val, attr_name: str, map_dict: Optional[dict]) -> Optional[int]:
        """
        Resolve a RADIUS attribute value to an integer.
        
        Args:
            val: The value to resolve
            attr_name: Name of the attribute
            map_dict: Optional dictionary to map string values to integers
            
        Returns:
            The resolved integer value, or None if explicit resolution fails
        """
        # If we got a byte string, decode it
        if isinstance(val, bytes):
            val = val.decode('utf-8')
        
        if isinstance(val, int):
            return val
        
        if isinstance(val, str):
            if val.isdigit():
                return int(val)
            if map_dict and val in map_dict:
                return map_dict[val]
            
            # Log if we can't parse it, specifically for Terminate-Cause
            if attr_name == 'Acct-Terminate-Cause':
                logger.warning(f"Could not map Acct-Terminate-Cause value '{val}'")
                
        try:
            return int(val)
        except (ValueError, TypeError):
            return None

    def _get_int_attribute(self, pkt: packet.AcctPacket, attr_name: str, 
                          map_dict: Optional[dict] = None) -> Optional[int]:
        """
        Get an integer attribute value from a packet.
        
        Args:
            pkt: The RADIUS packet
            attr_name: Name of the attribute to get
            map_dict: Optional dictionary to map string values to integers
            
        Returns:
            The attribute value as integer, or None if not found
        """
        try:
            values = pkt.get(attr_name)
            if values:
                return self._resolve_int_value(values[0], attr_name, map_dict)
                    
        except Exception as e:
            logger.debug(f"Error getting int attribute {attr_name}: {e}")
        return None
    
    def _create_response(self, request: packet.AcctPacket) -> packet.AcctPacket:
        """
        Create an Accounting-Response packet.
        
        Args:
            request: The original request packet
            
        Returns:
            Accounting-Response packet
        """
        return request.CreateReply()
