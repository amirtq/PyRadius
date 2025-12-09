"""
RADIUS Server

This module implements the main RADIUS UDP server that listens for
authentication and accounting requests from NAS clients.
"""

import logging
import os
import sys
import socket
import threading
from pathlib import Path

from pyrad import dictionary, packet, server

# Add parent directory to path for Django setup
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class NASHost:
    """
    Simple wrapper for NAS client that exposes the secret attribute.
    This is required by pyrad's internal Server._AddSecret method.
    """
    def __init__(self, secret):
        self.secret = secret


class DynamicHosts(dict):
    """
    Dictionary-like object that queries Django DB for NAS clients.
    """
    def __contains__(self, key):
        try:
            from nas.models import NASClient
            return NASClient.objects.filter(ip_address=key, is_active=True).exists()
        except Exception as e:
            logger.error(f"Error checking NAS client {key}: {e}")
            return False

    def __getitem__(self, key):
        try:
            from nas.models import NASClient
            # Use filter().first() to handle multiple clients safely
            nas = NASClient.objects.filter(ip_address=key, is_active=True).first()
            if nas:
                return NASHost(nas.get_secret_bytes())
            raise KeyError(key)
        except Exception:
            raise KeyError(key)


class RadiusServer(server.Server):
    """
    RADIUS Server implementation using pyrad.
    
    This server handles both authentication (port 1812) and
    accounting (port 1813) requests from NAS clients.
    """
    
    def __init__(self, hosts=None, dict_path=None, auth_port=1812, acct_port=1813,
                 bind_address='0.0.0.0'):
        """
        Initialize the RADIUS server.
        
        Args:
            hosts: Dictionary of allowed NAS clients (populated dynamically)
            dict_path: Path to RADIUS dictionary file
            auth_port: Authentication port (default 1812)
            acct_port: Accounting port (default 1813)
            bind_address: Address to bind to (default 0.0.0.0)
        """
        # Set up dictionary path
        if dict_path is None:
            dict_path = Path(__file__).parent / 'dictionary.txt'
        
        # Load RADIUS dictionary
        self.radius_dict = dictionary.Dictionary(str(dict_path))
        
        # Initialize dynamic hosts resolver
        self.hosts = DynamicHosts()
        
        # Initialize parent class
        super().__init__(
            dict=self.radius_dict,
            authport=auth_port,
            acctport=acct_port,
            hosts=self.hosts
        )
        
        self.bind_address = bind_address
        self.auth_port = auth_port
        self.acct_port = acct_port
        
        # Initialize handlers
        from radius.auth_handler import AuthenticationHandler
        from radius.acct_handler import AccountingHandler
        
        self.auth_handler = AuthenticationHandler(self.radius_dict)
        self.acct_handler = AccountingHandler(self.radius_dict)
        
        logger.info(f"RADIUS server initialized - Auth: {bind_address}:{auth_port}, "
                   f"Acct: {bind_address}:{acct_port}")

    def _get_nas_secret(self, nas_ip: str) -> bytes | None:
        """
        Get the shared secret for a NAS client.
        
        Args:
            nas_ip: IP address of the NAS
            
        Returns:
            Shared secret as bytes, or None if not found
        """
        try:
            from nas.models import NASClient
            nas = NASClient.get_by_ip(nas_ip)
            return nas.get_secret_bytes() if nas else None
        except Exception as e:
            logger.error(f"Error fetching NAS secret for {nas_ip}: {e}")
            return None

    def _AddSecret(self, pkt):
        """
        Override pyrad's _AddSecret to support multiple NAS clients with the same IP
        by also checking the NAS-Identifier.
        
        This method is called by pyrad before HandleAuth/AcctPacket.
        """
        try:
            ip = pkt.source[0]
            
            # Extract NAS-Identifier (Attribute 32)
            identifier = None
            if 32 in pkt:
                val = pkt[32]
                if val:
                    # val is a list of values, take first
                    try:
                        raw_id = val[0]
                        if isinstance(raw_id, bytes):
                            identifier = raw_id.decode('utf-8', errors='ignore')
                        else:
                            identifier = str(raw_id)
                    except Exception:
                        pass

            from nas.models import NASClient
            nas = NASClient.get_best_match(ip, identifier)
            
            if nas:
                pkt.secret = nas.get_secret_bytes()
            else:
                # If no NAS found, we don't set secret.
                # HandleAuthPacket/HandleAcctPacket should check for this.
                pass
                
        except Exception as e:
            logger.error(f"Error resolving NAS secret: {e}")

    def HandleAuthPacket(self, pkt):
        """
        Handle an incoming authentication packet.
        
        Args:
            pkt: The incoming RADIUS packet (AuthPacket)
        """
        logger.debug(f"Received auth packet from {pkt.source}")
        
        try:
            # Secret should have been set by _AddSecret
            if not getattr(pkt, 'secret', None):
                logger.warning(f"Unknown NAS client or secret not found: {pkt.source[0]}")
                return
            
            # Process the authentication request
            reply = self.auth_handler.handle_auth_request(pkt, pkt.source)
            
            # Set source on reply packet for pyrad
            reply.source = pkt.source  # type: ignore
            
            # Send the reply
            self.SendReplyPacket(pkt.fd, reply)
            
        except Exception as e:
            logger.exception(f"Error handling auth packet: {e}")
    
    def HandleAcctPacket(self, pkt):
        """
        Handle an incoming accounting packet.
        
        Args:
            pkt: The incoming RADIUS packet (AcctPacket)
        """
        logger.debug(f"Received acct packet from {pkt.source}")
        
        try:
            # Secret should have been set by _AddSecret
            if not getattr(pkt, 'secret', None):
                logger.warning(f"Unknown NAS client or secret not found: {pkt.source[0]}")
                return
            
            # Process the accounting request
            reply = self.acct_handler.handle_acct_request(pkt, pkt.source)
            
            # Set source on reply packet for pyrad
            reply.source = pkt.source  # type: ignore
            
            # Send the reply
            self.SendReplyPacket(pkt.fd, reply)
            
        except Exception as e:
            logger.exception(f"Error handling acct packet: {e}")
    
    def HandleCoaPacket(self, pkt):
        """
        Handle an incoming CoA (Change of Authorization) packet.
        
        Currently not implemented, but here for future use.
        
        Args:
            pkt: The incoming RADIUS packet
        """
        logger.debug(f"Received CoA packet from {pkt.source} - not implemented")
    
    def HandleDisconnectPacket(self, pkt):
        """
        Handle an incoming Disconnect packet.
        
        Currently not implemented, but here for future use.
        
        Args:
            pkt: The incoming RADIUS packet
        """
        logger.debug(f"Received disconnect packet from {pkt.source} - not implemented")


def setup_django():
    """
    Set up Django environment for standalone execution.
    """
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    
    import django
    django.setup()


def configure_logging(level='INFO'):
    """
    Configure logging for the RADIUS server.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def run_server(auth_port=1812, acct_port=1813, bind_address='0.0.0.0', log_level='INFO'):
    """
    Run the RADIUS server.
    
    Args:
        auth_port: Authentication port (default 1812)
        acct_port: Accounting port (default 1813)
        bind_address: Address to bind to (default 0.0.0.0)
        log_level: Logging level (default INFO)
    """
    # Configure logging
    configure_logging(log_level)
    
    # Set up Django
    setup_django()
    
    # Start the statistics scheduler
    try:
        from stats.scheduler import start_scheduler
        start_scheduler()
        logger.info("Statistics scheduler started")
    except Exception as e:
        logger.warning(f"Could not start statistics scheduler: {e}")
    
    logger.info("Starting RADIUS Server...")
    
    # Create and run the server
    try:
        srv = RadiusServer(
            auth_port=auth_port,
            acct_port=acct_port,
            bind_address=bind_address
        )
        
        # Bind to the specified address
        srv.BindToAddress(bind_address)
        
        logger.info("RADIUS server is running. Press Ctrl+C to stop.")
        srv.Run()
        
    except PermissionError:
        logger.error(f"Permission denied binding to ports {auth_port}/{acct_port}. "
                    f"Try running with elevated privileges or use ports > 1024.")
        sys.exit(1)
    except socket.error as e:
        logger.error(f"Socket error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("RADIUS server stopped.")
        sys.exit(0)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='RADIUS Server for OpenVPN')
    parser.add_argument('--auth-port', type=int, default=1812,
                       help='Authentication port (default: 1812)')
    parser.add_argument('--acct-port', type=int, default=1813,
                       help='Accounting port (default: 1813)')
    parser.add_argument('--bind', default='0.0.0.0',
                       help='Bind address (default: 0.0.0.0)')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level (default: INFO)')
    
    args = parser.parse_args()
    
    run_server(
        auth_port=args.auth_port,
        acct_port=args.acct_port,
        bind_address=args.bind,
        log_level=args.log_level
    )
