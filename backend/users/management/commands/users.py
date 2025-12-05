"""
Django management command for RADIUS user management.

Usage:
    python manage.py users create <username> <password> [options]
    python manage.py users list [options]
    python manage.py users delete <username>
    python manage.py users update <username> [options]
    python manage.py users show <username>
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date
from users.models import RadiusUser
from sessions.models import RadiusSession


class Command(BaseCommand):
    help = 'Manage RADIUS users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flushusers', '-fu', action='store_true',
            help='Completely clear the User table'
        )

        subparsers = parser.add_subparsers(dest='action', help='Action to perform')
        
        # Create user
        create_parser = subparsers.add_parser('create', help='Create a new user')
        create_parser.add_argument('username', type=str, help='Username')
        create_parser.add_argument('password', type=str, help='Password')
        create_parser.add_argument(
            '--max-sessions', '-m', type=int, default=1,
            help='Maximum concurrent sessions (default: 1)'
        )
        create_parser.add_argument(
            '--expires', '-e', type=str, default=None,
            help='Expiration date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)'
        )
        create_parser.add_argument(
            '--inactive', action='store_true',
            help='Create user as inactive'
        )
        create_parser.add_argument(
            '--notes', '-n', type=str, default='',
            help='Notes about the user'
        )
        
        # List users
        list_parser = subparsers.add_parser('list', help='List all users')
        list_parser.add_argument(
            '--active', '-a', action='store_true',
            help='Show only active users'
        )
        list_parser.add_argument(
            '--inactive', '-i', action='store_true',
            help='Show only inactive users'
        )
        list_parser.add_argument(
            '--expired', '-e', action='store_true',
            help='Show only expired users'
        )
        
        # Delete user
        delete_parser = subparsers.add_parser('delete', help='Delete a user')
        delete_parser.add_argument('username', type=str, help='Username to delete')
        delete_parser.add_argument(
            '--force', '-f', action='store_true',
            help='Force deletion without confirmation'
        )
        
        # Update user
        update_parser = subparsers.add_parser('update', help='Update a user')
        update_parser.add_argument('username', type=str, help='Username to update')
        update_parser.add_argument(
            '--password', '-p', type=str, default=None,
            help='New password'
        )
        update_parser.add_argument(
            '--max-sessions', '-m', type=int, default=None,
            help='Maximum concurrent sessions'
        )
        update_parser.add_argument(
            '--expires', '-e', type=str, default=None,
            help='Expiration date (YYYY-MM-DD or "never")'
        )
        update_parser.add_argument(
            '--active', action='store_true',
            help='Set user as active'
        )
        update_parser.add_argument(
            '--inactive', action='store_true',
            help='Set user as inactive'
        )
        update_parser.add_argument(
            '--notes', '-n', type=str, default=None,
            help='Notes about the user'
        )
        
        # Show user details
        show_parser = subparsers.add_parser('show', help='Show user details')
        show_parser.add_argument('username', type=str, help='Username to show')

    def handle(self, *args, **options):
        if options.get('flushusers'):
            self.clear_all_users(options)
            return

        action = options.get('action')
        
        if action == 'create':
            self.create_user(options)
        elif action == 'list':
            self.list_users(options)
        elif action == 'delete':
            self.delete_user(options)
        elif action == 'update':
            self.update_user(options)
        elif action == 'show':
            self.show_user(options)
        else:
            self.stdout.write(self.style.ERROR('Please specify an action: create, list, delete, update, show'))

    def create_user(self, options):
        """Create a new RADIUS user."""
        username = options['username']
        password = options['password']
        max_sessions = options['max_sessions']
        expires_str = options['expires']
        is_active = not options['inactive']
        notes = options['notes']
        
        # Check if user already exists
        if RadiusUser.objects.filter(username=username).exists():
            raise CommandError(f'User "{username}" already exists')
        
        # Parse expiration date
        expiration_date = None
        if expires_str:
            expiration_date = self._parse_date(expires_str)
        
        # Create user
        user = RadiusUser(
            username=username,
            max_concurrent_sessions=max_sessions,
            expiration_date=expiration_date,
            is_active=is_active,
            notes=notes
        )
        user.set_password(password)
        user.save()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created user "{username}"'))
        self._print_user_details(user)

    def list_users(self, options):
        """List all RADIUS users."""
        users = RadiusUser.objects.all()
        
        if options['active']:
            users = [u for u in users if u.is_active]
        elif options['inactive']:
            users = [u for u in users if not u.is_active]
            
        if options['expired']:
            users = [u for u in users if u.is_expired()]
        
        if not users:
            self.stdout.write('No users found')
            return
        
        # Print header
        self.stdout.write(
            f"{'Username':<20} {'Status':<10} {'Max Sessions':<12} "
            f"{'Active Sessions':<15} {'Expires':<20}"
        )
        self.stdout.write("-" * 80)
        
        for user in users:
            status = 'Active' if user.is_active else 'Inactive'
            if user.is_expired():
                status = 'Expired'
            
            active_sessions = user.get_active_session_count()
            expires = str(user.expiration_date.strftime('%Y-%m-%d %H:%M')) if user.expiration_date else 'Never'
            
            self.stdout.write(
                f"{user.username:<20} {status:<10} {user.max_concurrent_sessions:<12} "
                f"{active_sessions:<15} {expires:<20}"
            )
        
        self.stdout.write(f"\nTotal: {len(users)} user(s)")

    def delete_user(self, options):
        """Delete a RADIUS user."""
        username = options['username']
        force = options['force']
        
        try:
            user = RadiusUser.objects.get(username=username)
        except RadiusUser.DoesNotExist:
            raise CommandError(f'User "{username}" not found')
        
        # Check for active sessions
        active_sessions = user.get_active_session_count()
        if active_sessions > 0 and not force:
            raise CommandError(
                f'User "{username}" has {active_sessions} active session(s). '
                f'Use --force to delete anyway.'
            )
        
        if not force:
            confirm = input(f'Are you sure you want to delete user "{username}"? [y/N] ')
            if confirm.lower() != 'y':
                self.stdout.write('Cancelled')
                return
        
        user.delete()
        self.stdout.write(self.style.SUCCESS(f'Successfully deleted user "{username}"'))

    def update_user(self, options):
        """Update a RADIUS user."""
        username = options['username']
        
        try:
            user = RadiusUser.objects.get(username=username)
        except RadiusUser.DoesNotExist:
            raise CommandError(f'User "{username}" not found')
        
        updated = False
        
        if options['password']:
            user.set_password(options['password'])
            updated = True
            self.stdout.write('Password updated')
        
        if options['max_sessions'] is not None:
            user.max_concurrent_sessions = options['max_sessions']
            updated = True
            self.stdout.write(f'Max sessions set to {options["max_sessions"]}')
        
        if options['expires']:
            if options['expires'].lower() == 'never':
                user.expiration_date = None
                self.stdout.write('Expiration removed')
            else:
                user.expiration_date = self._parse_date(options['expires'])
                self.stdout.write(f'Expiration set to {user.expiration_date}')
            updated = True
        
        if options['active']:
            user.is_active = True
            updated = True
            self.stdout.write('User activated')
        elif options['inactive']:
            user.is_active = False
            updated = True
            self.stdout.write('User deactivated')
        
        if options['notes'] is not None:
            user.notes = options['notes']
            updated = True
            self.stdout.write('Notes updated')
        
        if updated:
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Successfully updated user "{username}"'))
        else:
            self.stdout.write('No changes made')

    def show_user(self, options):
        """Show details for a RADIUS user."""
        username = options['username']
        
        try:
            user = RadiusUser.objects.get(username=username)
        except RadiusUser.DoesNotExist:
            raise CommandError(f'User "{username}" not found')
        
        self._print_user_details(user)
        
        # Show active sessions
        sessions = RadiusSession.get_active_sessions_for_user(username)
        if sessions:
            self.stdout.write('\nActive Sessions:')
            self.stdout.write(f"  {'Session ID':<20} {'NAS':<15} {'IP Address':<15} {'Started':<20}")
            self.stdout.write("  " + "-" * 70)
            for session in sessions:
                self.stdout.write(
                    f"  {session.session_id:<20} {session.nas_identifier:<15} "
                    f"{session.framed_ip_address or 'N/A':<15} "
                    f"{session.start_time.strftime('%Y-%m-%d %H:%M:%S'):<20}"
                )

    def clear_all_users(self, options):
        """Clear all RADIUS users."""
        RadiusUser.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Successfully cleared all users'))

    def _print_user_details(self, user):
        """Print detailed user information."""
        status = 'Active' if user.is_active else 'Inactive'
        if user.is_expired():
            status = 'Expired'
        
        self.stdout.write(f"\nUser: {user.username}")
        self.stdout.write(f"  Status: {status}")
        self.stdout.write(f"  Max Concurrent Sessions: {user.max_concurrent_sessions}")
        self.stdout.write(f"  Active Sessions: {user.get_active_session_count()}")
        self.stdout.write(f"  Expiration: {user.expiration_date or 'Never'}")
        self.stdout.write(f"  Created: {user.created_at}")
        self.stdout.write(f"  Updated: {user.updated_at}")
        if user.notes:
            self.stdout.write(f"  Notes: {user.notes}")

    def _parse_date(self, date_str):
        """Parse a date string into a datetime object."""
        # Try datetime format first
        dt = parse_datetime(date_str)
        if dt:
            return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
        
        # Try date format
        d = parse_date(date_str)
        if d:
            return timezone.make_aware(
                timezone.datetime(d.year, d.month, d.day, 23, 59, 59)
            )
        
        raise CommandError(f'Invalid date format: {date_str}. Use YYYY-MM-DD or YYYY-MM-DD HH:MM:SS')
