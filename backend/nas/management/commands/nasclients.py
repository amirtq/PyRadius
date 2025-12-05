"""
Django management command for NAS client management (SQLite storage).

Usage:
    python manage.py nasclients add <identifier> <ip> <secret> [options]
    python manage.py nasclients list
    python manage.py nasclients delete <identifier>
    python manage.py nasclients update <identifier> [options]
    python manage.py nasclients show <identifier>
"""

from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError
from nas.models import NASClient


class Command(BaseCommand):
    help = 'Manage NAS (Network Access Server) clients using SQLite storage'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flushnas', '-fn', action='store_true',
            help='Completely clear the NAS table'
        )

        subparsers = parser.add_subparsers(dest='action', help='Action to perform')
        
        # Add NAS
        add_parser = subparsers.add_parser('add', help='Add a new NAS client')
        add_parser.add_argument('identifier', type=str, help='NAS identifier (e.g., myrouter)')
        add_parser.add_argument('ip', type=str, help='NAS IP address')
        add_parser.add_argument('secret', type=str, help='Shared secret')
        add_parser.add_argument(
            '--auth-port', type=int, default=1812,
            help='Authentication port (default: 1812)'
        )
        add_parser.add_argument(
            '--acct-port', type=int, default=1813,
            help='Accounting port (default: 1813)'
        )
        add_parser.add_argument(
            '--description', '-d', type=str, default='',
            help='Description of the NAS'
        )
        add_parser.add_argument(
            '--inactive', action='store_true',
            help='Create NAS as inactive'
        )
        
        # List NAS clients
        list_parser = subparsers.add_parser('list', help='List all NAS clients')
        list_parser.add_argument(
            '--active', '-a', action='store_true',
            help='Show only active NAS clients'
        )
        
        # Delete NAS
        delete_parser = subparsers.add_parser('delete', help='Delete a NAS client')
        delete_parser.add_argument('identifier', type=str, help='NAS identifier to delete')
        delete_parser.add_argument(
            '--force', '-f', action='store_true',
            help='Force deletion without confirmation'
        )
        
        # Update NAS
        update_parser = subparsers.add_parser('update', help='Update a NAS client')
        update_parser.add_argument('identifier', type=str, help='NAS identifier to update')
        update_parser.add_argument(
            '--ip', type=str, default=None,
            help='New IP address'
        )
        update_parser.add_argument(
            '--secret', type=str, default=None,
            help='New shared secret'
        )
        update_parser.add_argument(
            '--auth-port', type=int, default=None,
            help='New authentication port'
        )
        update_parser.add_argument(
            '--acct-port', type=int, default=None,
            help='New accounting port'
        )
        update_parser.add_argument(
            '--description', '-d', type=str, default=None,
            help='New description'
        )
        update_parser.add_argument(
            '--active', action='store_true',
            help='Set NAS as active'
        )
        update_parser.add_argument(
            '--inactive', action='store_true',
            help='Set NAS as inactive'
        )
        
        # Show NAS details
        show_parser = subparsers.add_parser('show', help='Show NAS details')
        show_parser.add_argument('identifier', type=str, help='NAS identifier to show')

    def handle(self, *args, **options):
        if options.get('flushnas'):
            self.clear_all_nas()
            return

        action = options.get('action')
        
        if action == 'add':
            self.add_nas(options)
        elif action == 'list':
            self.list_nas(options)
        elif action == 'delete':
            self.delete_nas(options)
        elif action == 'update':
            self.update_nas(options)
        elif action == 'show':
            self.show_nas(options)
        else:
            self.stdout.write(self.style.ERROR('Please specify an action: add, list, delete, update, show'))

    def add_nas(self, options):
        identifier = options['identifier']
        ip = options['ip']
        
        # Check uniqueness
        if NASClient.objects.filter(identifier=identifier).exists():
            raise CommandError(f'NAS "{identifier}" already exists')
        
        if NASClient.objects.filter(ip_address=ip).exists():
            raise CommandError(f'NAS IP "{ip}" already exists')

        try:
            new_nas = NASClient.objects.create(
                identifier=identifier,
                ip_address=ip,
                shared_secret=options['secret'],
                auth_port=options['auth_port'],
                acct_port=options['acct_port'],
                description=options['description'],
                is_active=not options['inactive']
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully added NAS "{identifier}"'))
            self._print_nas_details(new_nas)
        except Exception as e:
            raise CommandError(f'Error adding NAS: {e}')

    def list_nas(self, options):
        queryset = NASClient.objects.all()
        
        if options.get('active'):
            queryset = queryset.filter(is_active=True)
            
        if not queryset.exists():
            self.stdout.write('No NAS clients found')
            return

        self.stdout.write(
            f"{'Identifier':<20} {'IP Address':<15} {'Status':<10} "
            f"{'Auth Port':<10} {'Acct Port':<10}"
        )
        self.stdout.write("-" * 70)
        
        for nas in queryset:
            status = 'Active' if nas.is_active else 'Inactive'
            self.stdout.write(
                f"{nas.identifier:<20} {nas.ip_address:<15} {status:<10} "
                f"{nas.auth_port:<10} {nas.acct_port:<10}"
            )
        self.stdout.write(f"\nTotal: {queryset.count()} NAS client(s)")

    def delete_nas(self, options):
        identifier = options['identifier']
        
        try:
            nas = NASClient.objects.get(identifier=identifier)
            
            if not options['force']:
                confirm = input(f'Are you sure you want to delete NAS "{identifier}"? [y/N] ')
                if confirm.lower() != 'y':
                    self.stdout.write('Cancelled')
                    return
            
            nas.delete()
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted NAS "{identifier}"'))
            
        except NASClient.DoesNotExist:
            raise CommandError(f'NAS "{identifier}" not found')

    def update_nas(self, options):
        identifier = options['identifier']
        
        try:
            nas = NASClient.objects.get(identifier=identifier)
            updated = False
            
            if options['ip']:
                nas.ip_address = options['ip']
                updated = True
            if options['secret']:
                nas.shared_secret = options['secret']
                updated = True
            if options['auth_port'] is not None:
                nas.auth_port = options['auth_port']
                updated = True
            if options['acct_port'] is not None:
                nas.acct_port = options['acct_port']
                updated = True
            if options['description'] is not None:
                nas.description = options['description']
                updated = True
            if options['active']:
                nas.is_active = True
                updated = True
            elif options['inactive']:
                nas.is_active = False
                updated = True
                
            if updated:
                nas.save()
                self.stdout.write(self.style.SUCCESS(f'Successfully updated NAS "{identifier}"'))
            else:
                self.stdout.write('No changes made')
                
        except NASClient.DoesNotExist:
            raise CommandError(f'NAS "{identifier}" not found')
        except IntegrityError as e:
            raise CommandError(f'Error updating NAS: {e}')

    def show_nas(self, options):
        identifier = options['identifier']
        
        try:
            nas = NASClient.objects.get(identifier=identifier)
            self._print_nas_details(nas)
        except NASClient.DoesNotExist:
            raise CommandError(f'NAS "{identifier}" not found')

    def clear_all_nas(self):
        """Clear all NAS clients."""
        NASClient.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Successfully cleared all NAS clients'))

    def _print_nas_details(self, nas):
        status = 'Active' if nas.is_active else 'Inactive'
        self.stdout.write(f"\nNAS: {nas.identifier}")
        self.stdout.write(f"  IP Address: {nas.ip_address}")
        self.stdout.write(f"  Status: {status}")
        self.stdout.write(f"  Auth Port: {nas.auth_port}")
        self.stdout.write(f"  Acct Port: {nas.acct_port}")
        self.stdout.write(f"  Shared Secret: {'*' * len(nas.shared_secret)}")
        self.stdout.write(f"  Created: {nas.created_at}")
        self.stdout.write(f"  Updated: {nas.updated_at}")
        if nas.description:
            self.stdout.write(f"  Description: {nas.description}")
