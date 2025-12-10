"""
Session Buffer Module

This module provides a thread-safe queue-based buffer for session operations.
Instead of writing to the database immediately, operations are queued and
flushed periodically to improve performance.
"""

import logging
import queue
import threading
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


class OperationType(Enum):
    """Types of session operations."""
    START = 'start'
    UPDATE = 'update'
    STOP = 'stop'


@dataclass
class SessionOperation:
    """Represents a single session operation."""
    op_type: OperationType
    session_id: str
    nas_ip_address: str
    username: str
    timestamp: datetime = field(default_factory=timezone.now)
    data: Dict[str, Any] = field(default_factory=dict)


class SessionBuffer:
    """
    Thread-safe queue-based buffer for session operations.
    
    Operations are stored in a queue and flushed periodically to the database.
    This reduces database I/O by batching multiple operations into single transactions.
    """
    
    _instance: Optional['SessionBuffer'] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> 'SessionBuffer':
        """Singleton pattern to ensure only one buffer exists."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the session buffer."""
        if self._initialized:
            return
            
        self._queue: queue.Queue[SessionOperation] = queue.Queue()
        # In-memory state for quick lookups (session_id -> latest operation)
        self._pending_state: Dict[Tuple[str, str], SessionOperation] = {}
        self._state_lock = threading.RLock()
        self._initialized = True
        self._shutdown = False
        
        logger.info("Session buffer initialized")
    
    def add_start(
        self,
        session_id: str,
        username: str,
        nas_ip_address: str,
        nas_identifier: str = '',
        framed_ip_address: Optional[str] = None,
        calling_station_id: str = ''
    ) -> None:
        """
        Queue a session start operation.
        
        Args:
            session_id: Unique session identifier
            username: Username of the connected user
            nas_ip_address: NAS IP address
            nas_identifier: NAS identifier
            framed_ip_address: Assigned IP address
            calling_station_id: Client identifier
        """
        operation = SessionOperation(
            op_type=OperationType.START,
            session_id=session_id,
            nas_ip_address=nas_ip_address,
            username=username,
            data={
                'nas_identifier': nas_identifier,
                'framed_ip_address': framed_ip_address,
                'calling_station_id': calling_station_id,
            }
        )
        
        self._queue.put(operation)
        
        # Update in-memory state for quick lookups
        key = (session_id, nas_ip_address)
        with self._state_lock:
            self._pending_state[key] = operation
            
        logger.debug(f"Queued session START: {session_id} for user {username}")
    
    def add_update(
        self,
        session_id: str,
        nas_ip_address: str,
        username: str,
        session_time: Optional[int] = None,
        input_octets: Optional[int] = None,
        output_octets: Optional[int] = None,
        input_packets: Optional[int] = None,
        output_packets: Optional[int] = None
    ) -> None:
        """
        Queue a session update operation.
        
        Args:
            session_id: Session identifier
            nas_ip_address: NAS IP address
            username: Username
            session_time: Session duration in seconds
            input_octets: Bytes received
            output_octets: Bytes sent
            input_packets: Packets received
            output_packets: Packets sent
        """
        data = {}
        if session_time is not None:
            data['session_time'] = session_time
        if input_octets is not None:
            data['input_octets'] = input_octets
        if output_octets is not None:
            data['output_octets'] = output_octets
        if input_packets is not None:
            data['input_packets'] = input_packets
        if output_packets is not None:
            data['output_packets'] = output_packets
        
        operation = SessionOperation(
            op_type=OperationType.UPDATE,
            session_id=session_id,
            nas_ip_address=nas_ip_address,
            username=username,
            data=data
        )
        
        self._queue.put(operation)
        
        # Update in-memory state
        key = (session_id, nas_ip_address)
        with self._state_lock:
            if key in self._pending_state:
                # Merge update into existing state
                self._pending_state[key].data.update(data)
            else:
                self._pending_state[key] = operation
                
        logger.debug(f"Queued session UPDATE: {session_id}")
    
    def add_stop(
        self,
        session_id: str,
        nas_ip_address: str,
        username: str,
        terminate_cause: Optional[int] = None,
        session_time: Optional[int] = None,
        input_octets: Optional[int] = None,
        output_octets: Optional[int] = None,
        input_packets: Optional[int] = None,
        output_packets: Optional[int] = None
    ) -> None:
        """
        Queue a session stop operation.
        
        Args:
            session_id: Session identifier
            nas_ip_address: NAS IP address
            username: Username
            terminate_cause: Termination cause code
            session_time: Session duration
            input_octets: Bytes received
            output_octets: Bytes sent
            input_packets: Packets received
            output_packets: Packets sent
        """
        data = {}
        if terminate_cause is not None:
            data['terminate_cause'] = terminate_cause
        if session_time is not None:
            data['session_time'] = session_time
        if input_octets is not None:
            data['input_octets'] = input_octets
        if output_octets is not None:
            data['output_octets'] = output_octets
        if input_packets is not None:
            data['input_packets'] = input_packets
        if output_packets is not None:
            data['output_packets'] = output_packets
        
        operation = SessionOperation(
            op_type=OperationType.STOP,
            session_id=session_id,
            nas_ip_address=nas_ip_address,
            username=username,
            data=data
        )
        
        self._queue.put(operation)
        
        # Update in-memory state - mark as stopped
        key = (session_id, nas_ip_address)
        with self._state_lock:
            self._pending_state[key] = operation
            
        logger.debug(f"Queued session STOP: {session_id}")
    
    def get_pending_session_count(self, username: str) -> int:
        """
        Count pending active sessions for a user in the buffer.
        
        This is used to supplement the database count when checking
        concurrent session limits.
        
        Args:
            username: Username to count sessions for
            
        Returns:
            Net count of active sessions in the buffer (starts - stops)
        """
        with self._state_lock:
            count = 0
            for key, op in self._pending_state.items():
                if op.username == username:
                    if op.op_type == OperationType.START:
                        count += 1
                    elif op.op_type == OperationType.STOP:
                        count -= 1
            return count
    
    def is_session_pending(self, session_id: str, nas_ip_address: str) -> bool:
        """
        Check if a session exists in the pending buffer.
        
        Args:
            session_id: Session identifier
            nas_ip_address: NAS IP address
            
        Returns:
            True if session is pending (not yet flushed to DB)
        """
        key = (session_id, nas_ip_address)
        with self._state_lock:
            if key in self._pending_state:
                return self._pending_state[key].op_type != OperationType.STOP
        return False
    
    def flush(self) -> int:
        """
        Flush all pending operations to the database.
        
        Operations are merged by session_id to avoid redundant writes.
        For example, if START + UPDATE + STOP occur for the same session
        within a flush interval, we write a single stopped session.
        
        Returns:
            Number of operations processed
        """
        # Drain the queue
        operations: List[SessionOperation] = []
        while True:
            try:
                operations.append(self._queue.get_nowait())
            except queue.Empty:
                break
        
        if not operations:
            return 0
        
        # Merge operations by session
        merged = self._merge_operations(operations)
        
        # Clear pending state for flushed operations
        with self._state_lock:
            for key in merged.keys():
                self._pending_state.pop(key, None)
        
        # Write to database
        processed = self._write_to_database(merged)
        
        logger.info(f"Flushed {processed} session operations to database")
        return processed
    
    def _merge_operations(
        self,
        operations: List[SessionOperation]
    ) -> Dict[Tuple[str, str], SessionOperation]:
        """
        Merge operations for the same session.
        
        Args:
            operations: List of session operations
            
        Returns:
            Dictionary mapping (session_id, nas_ip) to final merged operation
        """
        merged: Dict[Tuple[str, str], SessionOperation] = {}
        
        for op in operations:
            key = (op.session_id, op.nas_ip_address)
            
            if key not in merged:
                merged[key] = op
            else:
                existing = merged[key]
                
                if op.op_type == OperationType.STOP:
                    # STOP always wins - merge data into stop operation
                    op.data = {**existing.data, **op.data}
                    if existing.op_type == OperationType.START:
                        # Session started and stopped in same interval
                        op.data['_created_and_stopped'] = True
                    merged[key] = op
                elif op.op_type == OperationType.UPDATE:
                    # Merge update data into existing
                    existing.data.update(op.data)
                # START operations don't override existing START
        
        return merged
    
    def _write_to_database(
        self,
        merged: Dict[Tuple[str, str], SessionOperation]
    ) -> int:
        """
        Write merged operations to the database.
        
        Args:
            merged: Merged operations dictionary
            
        Returns:
            Number of operations written
        """
        from sessions.models import RadiusSession
        from users.models import RadiusUser
        
        processed = 0
        affected_users: set = set()
        
        try:
            with transaction.atomic():
                for key, op in merged.items():
                    session_id, nas_ip = key
                    
                    try:
                        if op.op_type == OperationType.START:
                            self._process_start(op)
                            affected_users.add(op.username)
                            processed += 1
                            
                        elif op.op_type == OperationType.UPDATE:
                            self._process_update(op)
                            processed += 1
                            
                        elif op.op_type == OperationType.STOP:
                            if op.data.get('_created_and_stopped'):
                                # Create session as stopped
                                self._process_start_and_stop(op)
                            else:
                                self._process_stop(op)
                            affected_users.add(op.username)
                            processed += 1
                            
                    except Exception as e:
                        logger.error(f"Error processing operation {op}: {e}")
                
                # Update session counts for affected users
                for username in affected_users:
                    try:
                        user = RadiusUser.objects.get(username=username)
                        user.update_session_counts()
                    except RadiusUser.DoesNotExist:
                        pass
                        
        except Exception as e:
            logger.error(f"Error during flush transaction: {e}")
        
        return processed
    
    def _process_start(self, op: SessionOperation) -> None:
        """Process a session start operation."""
        from sessions.models import RadiusSession
        
        # Check if session already exists
        existing = RadiusSession.find_session(op.session_id, op.nas_ip_address)
        if existing:
            logger.warning(f"Session {op.session_id} already exists, skipping start")
            return
        
        # Check for stale sessions with same Framed-IP
        framed_ip = op.data.get('framed_ip_address')
        if framed_ip:
            stale_sessions = RadiusSession.objects.filter(
                username=op.username,
                status=RadiusSession.STATUS_ACTIVE,
                framed_ip_address=framed_ip
            ).exclude(session_id=op.session_id)
            
            for stale in stale_sessions:
                logger.info(f"Closing stale session {stale.session_id} for user {op.username}")
                stale.stop_session(terminate_cause=RadiusSession.TERMINATE_CAUSE_NAS_REQUEST)
        
        # Create new session
        RadiusSession.objects.create(
            session_id=op.session_id,
            username=op.username,
            nas_identifier=op.data.get('nas_identifier', ''),
            nas_ip_address=op.nas_ip_address,
            framed_ip_address=framed_ip,
            calling_station_id=op.data.get('calling_station_id', ''),
            status=RadiusSession.STATUS_ACTIVE,
            start_time=op.timestamp
        )
    
    def _process_update(self, op: SessionOperation) -> None:
        """Process a session update operation."""
        from sessions.models import RadiusSession
        
        session = RadiusSession.find_session(op.session_id, op.nas_ip_address)
        if not session:
            logger.warning(f"Session {op.session_id} not found for update")
            return
        
        # Get statistics
        session_time = op.data.get('session_time')
        input_octets = op.data.get('input_octets')
        output_octets = op.data.get('output_octets')
        input_packets = op.data.get('input_packets')
        output_packets = op.data.get('output_packets')
        
        # Update session statistics
        update_kwargs = {}
        if session_time is not None:
            update_kwargs['session_time'] = session_time
        if input_octets is not None:
            update_kwargs['input_octets'] = input_octets
        if output_octets is not None:
            update_kwargs['output_octets'] = output_octets
        if input_packets is not None:
            update_kwargs['input_packets'] = input_packets
        if output_packets is not None:
            update_kwargs['output_packets'] = output_packets
        
        if update_kwargs:
            session.update_statistics(**update_kwargs)
    
    def _process_stop(self, op: SessionOperation) -> None:
        """Process a session stop operation."""
        from sessions.models import RadiusSession
        
        session = RadiusSession.find_session(op.session_id, op.nas_ip_address)
        if not session:
            logger.warning(f"Session {op.session_id} not found for stop")
            return
        
        # Build stop arguments
        stop_kwargs = {}
        if 'terminate_cause' in op.data:
            stop_kwargs['terminate_cause'] = op.data['terminate_cause']
        if 'session_time' in op.data:
            stop_kwargs['session_time'] = op.data['session_time']
        if 'input_octets' in op.data:
            stop_kwargs['input_octets'] = op.data['input_octets']
        if 'output_octets' in op.data:
            stop_kwargs['output_octets'] = op.data['output_octets']
        if 'input_packets' in op.data:
            stop_kwargs['input_packets'] = op.data['input_packets']
        if 'output_packets' in op.data:
            stop_kwargs['output_packets'] = op.data['output_packets']
        
        session.stop_session(**stop_kwargs)
    
    def _process_start_and_stop(self, op: SessionOperation) -> None:
        """Process a session that started and stopped in the same interval."""
        from sessions.models import RadiusSession
        
        # Check if session already exists
        existing = RadiusSession.find_session(op.session_id, op.nas_ip_address)
        if existing:
            # Just stop it
            self._process_stop(op)
            return
        
        # Create session as already stopped
        session = RadiusSession.objects.create(
            session_id=op.session_id,
            username=op.username,
            nas_identifier=op.data.get('nas_identifier', ''),
            nas_ip_address=op.nas_ip_address,
            framed_ip_address=op.data.get('framed_ip_address'),
            calling_station_id=op.data.get('calling_station_id', ''),
            status=RadiusSession.STATUS_STOPPED,
            start_time=op.timestamp,
            stop_time=timezone.now(),
            terminate_cause=op.data.get('terminate_cause'),
            session_time=op.data.get('session_time', 0),
            input_octets=op.data.get('input_octets', 0),
            output_octets=op.data.get('output_octets', 0),
            input_packets=op.data.get('input_packets', 0),
            output_packets=op.data.get('output_packets', 0)
        )
    
    def shutdown(self) -> None:
        """
        Gracefully shutdown the buffer, flushing all pending operations.
        """
        if self._shutdown:
            return
            
        self._shutdown = True
        logger.info("Shutting down session buffer, flushing remaining operations...")
        
        # Flush any remaining operations
        count = self.flush()
        logger.info(f"Session buffer shutdown complete, flushed {count} operations")


# Global buffer instance
def get_session_buffer() -> SessionBuffer:
    """Get the global session buffer instance."""
    return SessionBuffer()
