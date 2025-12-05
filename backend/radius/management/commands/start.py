"""
Django management command to run the RADIUS server.

Usage:
    python manage.py start [options]
"""

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Run the RADIUS server'

    def add_arguments(self, parser):
        parser.add_argument(
            '--auth-port', type=int, default=None,
            help='Authentication port (default: from settings or 1812)'
        )
        parser.add_argument(
            '--acct-port', type=int, default=None,
            help='Accounting port (default: from settings or 1813)'
        )
        parser.add_argument(
            '--bind', type=str, default=None,
            help='Bind address (default: from settings or 0.0.0.0)'
        )
        parser.add_argument(
            '--log-level', type=str, default=None,
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            help='Logging level (default: from settings or INFO)'
        )

    def handle(self, *args, **options):
        from radius.server import run_server
        
        # Get configuration from settings with command-line overrides
        radius_config = getattr(settings, 'RADIUS_CONFIG', {})
        
        auth_port = options['auth_port'] or radius_config.get('AUTH_PORT', 1812)
        acct_port = options['acct_port'] or radius_config.get('ACCT_PORT', 1813)
        bind_address = options['bind'] or radius_config.get('BIND_ADDRESS', '0.0.0.0')
        log_level = options['log_level'] or radius_config.get('LOG_LEVEL', 'INFO')
        
        self.stdout.write(self.style.SUCCESS('Starting RADIUS Server...'))
        self.stdout.write(f'  Authentication port: {auth_port}')
        self.stdout.write(f'  Accounting port: {acct_port}')
        self.stdout.write(f'  Bind address: {bind_address}')
        self.stdout.write(f'  Log level: {log_level}')
        self.stdout.write('')
        
        # Run the server (this will block until interrupted)
        run_server(
            auth_port=auth_port,
            acct_port=acct_port,
            bind_address=bind_address,
            log_level=log_level
        )
