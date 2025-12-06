"""
Django management command for RADIUS user management.

Usage:
    python manage.py users add <username> <password> [options]
    python manage.py users list [options]
    python manage.py users delete <username>
    python manage.py users update <username> [options]
    python manage.py users show <username>
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateparse import parse_datetime, parse_date
from users.models import RadiusUser, AdminUser
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
        create_parser = subparsers.add_parser('add', help='Create a new user')
        
        # User type selection for add
        add_type_group = create_parser.add_mutually_exclusive_group(required=True)
        add_type_group.add_argument(
            '--radius-user', '--radius', action='store_true',
            help='Create a RADIUS user'
        )
        add_type_group.add_argument(
            '--admin-user', '--admin', action='store_true',
            help='Create an Admin user'
        )

        create_parser.add_argument('username', type=str, help='Username')
        create_parser.add_argument('password', type=str, help='Password')
        create_parser.add_argument(
            '--clear-text-password', '-ctp', action='store_true',
            help='Store password in clear text (prefixed with ctp:)'
        )
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
        create_parser.add_argument(
            '--traffic-limit', '-t', type=str, default=None,
            help='Traffic limit (e.g. 5G, 100M)'
        )
        
        # List users
        list_parser = subparsers.add_parser('list', help='List all users')
        
        # User type selection for list (optional)
        list_type_group = list_parser.add_mutually_exclusive_group(required=False)
        list_type_group.add_argument(
            '--radius-user', '--radius', action='store_true',
            help='List only RADIUS users'
        )
        list_type_group.add_argument(
            '--admin-user', '--admin', action='store_true',
            help='List only Admin users'
        )

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
        
        # User type selection for update
        update_type_group = update_parser.add_mutually_exclusive_group(required=True)
        update_type_group.add_argument(
            '--radius-user', '--radius', action='store_true',
            help='Update a RADIUS user'
        )
        update_type_group.add_argument(
            '--admin-user', '--admin', action='store_true',
            help='Update an Admin user'
        )

        update_parser.add_argument('username', type=str, help='Username to update')
        update_parser.add_argument(
            '--password', '-p', type=str, default=None,
            help='New password'
        )
        update_parser.add_argument(
            '--clear-text-password', '-ctp', action='store_true',
            help='Store password in clear text (prefixed with ctp:)'
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
        update_parser.add_argument(
            '--traffic-limit', '-t', type=str, default=None,
            help='Traffic limit (e.g. 5G, 100M, or "unlimited")'
        )
        
        # Show user details
        show_parser = subparsers.add_parser('show', help='Show user details')
        show_parser.add_argument('username', type=str, help='Username to show')

    def handle(self, *args, **options):
        if options.get('flushusers'):
            self.clear_all_users(options)
            return

        action = options.get('action')
        
        if action == 'add':
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
            self.stdout.write(self.style.ERROR('Please specify an action: add, list, delete, update, show'))

    def create_user(self, options):
        """Create a new user (Radius or Admin)."""
        if options.get('admin_user'):
            self._create_admin_user(options)
        else:
            self._create_radius_user(options)

    def _create_admin_user(self, options):
        """Helper to create an Admin user with validation."""
        username = options['username']
        password = options['password']

        # Validate Admin user specific constraints
        if options.get('clear_text_password'):
            raise CommandError("Admin users cannot have clear text passwords")
        
        if options.get('max_sessions') != 1:
            raise CommandError("Admin users do not support 'max-sessions'")
        
        if options.get('expires'):
            raise CommandError("Admin users do not support 'expires'")
        
        if options.get('inactive'):
            raise CommandError("Admin users do not support 'inactive' flag during creation")
        
        if options.get('notes'):
            raise CommandError("Admin users do not support 'notes'")
        
        if options.get('traffic_limit'):
            raise CommandError("Admin users do not support 'traffic-limit'")
        
        # Check if user already exists
        if AdminUser.objects.filter(username=username).exists():
            raise CommandError(f'Admin user "{username}" already exists')

        # Create Admin user
        AdminUser.objects.create_superuser(username=username, password=password)  # type: ignore
        self.stdout.write(self.style.SUCCESS(f'Successfully created admin user "{username}"'))

    def _create_radius_user(self, options):
        """Helper to create a RADIUS user."""
        username = options['username']
        password = options['password']

        # Radius User Creation Logic
        use_cleartext = options.get('clear_text_password')
        max_sessions = options.get('max_sessions')
        expires_str = options.get('expires')
        is_active = not options.get('inactive')
        notes = options.get('notes')
        allowed_traffic = self._parse_traffic(options.get('traffic_limit'))
        
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
            notes=notes,
            allowed_traffic=allowed_traffic
        )
        user.set_password(password, use_cleartext=use_cleartext)
        user.save()
        
        self.stdout.write(self.style.SUCCESS(f'Successfully created user "{username}"'))
        self._print_user_details(user)

    def list_users(self, options):
        """List users based on selection."""
        show_radius = options.get('radius_user')
        show_admin = options.get('admin_user')

        # If neither is selected, show both (default)
        if not show_radius and not show_admin:
            self._list_radius_users(options)
            self.stdout.write("\n")
            self._list_admin_users(options)
            return

        if show_radius:
            self._list_radius_users(options)
        
        if show_admin:
            self._list_admin_users(options)

    def _list_radius_users(self, options):
        """List all RADIUS users."""
        users = self._filter_radius_users(options)
        
        self.stdout.write(self.style.SUCCESS('RADIUS Users:'))
        
        if not users:
            self.stdout.write('No RADIUS users found')
            return
        
        # Print header
        self.stdout.write(
            f"{'Username':<20} {'Password':<15} {'Status':<10} {'ExpDate':<16} {'MaxConnections':<16} {'ActiveConnections':<18} "
            f"{'TotalQuota':<12} {'RX':<10} {'TX':<10} {'UsedQuota':<10} {'RemainingQuota':<10}"
        )
        self.stdout.write("-" * 160)
        
        for user in users:
            self._print_user_row(user)
        
        self.stdout.write(f"Total: {len(users)} RADIUS user(s)")

    def _list_admin_users(self, options):
        """List all Admin users."""
        users = AdminUser.objects.all()
        
        # Apply filters
        if options.get('active'):
            users = users.filter(is_active=True)
        elif options.get('inactive'):
            users = users.filter(is_active=False)
        
        # Note: Expired filter only applies to Radius users, ignored here

        self.stdout.write(self.style.SUCCESS('Admin Users:'))

        if not users.exists():
            self.stdout.write('No admin users found')
            return

        self.stdout.write(f"{'ID':<5} {'Username':<20} {'Is Active':<10}")
        self.stdout.write("-" * 40)
        
        for user in users:
            self.stdout.write(f"{user.pk:<5} {user.username:<20} {str(user.is_active):<10}")
        
        self.stdout.write(f"Total: {users.count()} admin user(s)")


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
        """Update a user (Radius or Admin)."""
        if options.get('admin_user'):
            self._update_admin_user(options)
        else:
            self._update_radius_user(options)

    def _update_admin_user(self, options):
        """Helper to update an Admin user."""
        username = options['username']
        try:
            user = AdminUser.objects.get(username=username)
        except AdminUser.DoesNotExist:
            raise CommandError(f'Admin user "{username}" not found')

        # Validate incompatible options
        if options.get('clear_text_password'):
            raise CommandError("Admin users cannot have clear text passwords")
        if options.get('max_sessions'):
            raise CommandError("Admin users do not support 'max-sessions'")
        if options.get('expires'):
             raise CommandError("Admin users do not support 'expires'")
        if options.get('notes'):
             raise CommandError("Admin users do not support 'notes'")
        if options.get('traffic_limit'):
             raise CommandError("Admin users do not support 'traffic-limit'")
        
        updated = False
        # Password Update
        if options.get('password'):
             user.set_password(options['password'])
             self.stdout.write('Password updated')
             updated = True
        
        # Status Update
        if options.get('active'):
             user.is_active = True
             self.stdout.write('User activated')
             updated = True
        elif options.get('inactive'):
             user.is_active = False
             self.stdout.write('User deactivated')
             updated = True
        
        if updated:
             user.save()
             self.stdout.write(self.style.SUCCESS(f'Successfully updated admin user "{username}"'))
        else:
             self.stdout.write('No changes made')

    def _update_radius_user(self, options):
        """Helper to update a RADIUS user."""
        username = options['username']
        try:
            user = RadiusUser.objects.get(username=username)
        except RadiusUser.DoesNotExist:
            raise CommandError(f'User "{username}" not found')
        
        updated = False
        updated |= self._handle_password_update(user, options['password'], options['clear_text_password'])
        updated |= self._handle_max_sessions_update(user, options['max_sessions'])
        updated |= self._handle_expiration_update(user, options['expires'])
        updated |= self._handle_status_update(user, options)
        updated |= self._handle_notes_update(user, options['notes'])
        updated |= self._handle_traffic_limit_update(user, options.get('traffic_limit'))

        if updated:
            user.save()
            self.stdout.write(self.style.SUCCESS(f'Successfully updated user "{username}"'))
        else:
            self.stdout.write('No changes made')

    def _handle_password_update(self, user, password, use_cleartext=False):
        if password:
            user.set_password(password, use_cleartext=use_cleartext)
            self.stdout.write('Password updated')
            return True
        return False

    def _handle_max_sessions_update(self, user, max_sessions):
        if max_sessions is not None:
            user.max_concurrent_sessions = max_sessions
            self.stdout.write(f'Max sessions set to {max_sessions}')
            return True
        return False

    def _handle_expiration_update(self, user, expires):
        if expires:
            if expires.lower() == 'never':
                user.expiration_date = None
                self.stdout.write('Expiration removed')
            else:
                user.expiration_date = self._parse_date(expires)
                self.stdout.write(f'Expiration set to {user.expiration_date}')
            return True
        return False

    def _handle_status_update(self, user, options):
        if options['active']:
            user.is_active = True
            self.stdout.write('User activated')
            return True
        elif options['inactive']:
            user.is_active = False
            self.stdout.write('User deactivated')
            return True
        return False

    def _handle_notes_update(self, user, notes):
        if notes is not None:
            user.notes = notes
            self.stdout.write('Notes updated')
            return True
        return False

    def _handle_traffic_limit_update(self, user, traffic_limit):
        if traffic_limit is not None:
            if traffic_limit.lower() == 'unlimited':
                user.allowed_traffic = None
                self.stdout.write('Traffic limit removed')
            else:
                user.allowed_traffic = self._parse_traffic(traffic_limit)
                self.stdout.write(f'Traffic limit set to {self._format_bytes(user.allowed_traffic)}')
            return True
        return False

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
        status = 'OK'
        if not user.is_active:
            status = 'Disabled'
        elif user.is_expired():
            status = 'Expired'
        elif user.allowed_traffic is not None and user.total_traffic >= user.allowed_traffic:
            status = 'OverQuota'
        
        self.stdout.write(f"\nUser: {user.username}")
        self.stdout.write(f"  Status: {status}")
        self.stdout.write(f"  Max Concurrent Sessions: {user.max_concurrent_sessions}")
        self.stdout.write(f"  Active Sessions: {user.get_active_session_count()}")
        
        self.stdout.write("  Traffic:")
        self.stdout.write(f"    RX: {self._format_bytes(user.rx_traffic)}")
        self.stdout.write(f"    TX: {self._format_bytes(user.tx_traffic)}")
        self.stdout.write(f"    Total: {self._format_bytes(user.total_traffic)}")
        limit = self._format_bytes(user.allowed_traffic) if user.allowed_traffic else 'Unlimited'
        self.stdout.write(f"    Limit: {limit}")
        if user.allowed_traffic:
            remaining = user.allowed_traffic - user.total_traffic
            if remaining < 0: remaining = 0
            self.stdout.write(f"    Remaining: {self._format_bytes(remaining)}")

        self.stdout.write(f"  Expiration: {user.expiration_date or 'Never'}")
        self.stdout.write(f"  Created: {user.created_at}")
        self.stdout.write(f"  Updated: {user.updated_at}")
        if user.notes:
            self.stdout.write(f"  Notes: {user.notes}")

    def _parse_traffic(self, size_str):
        """Parse a traffic size string (e.g. "1G", "500M") into bytes."""
        if not size_str:
            return None
        
        size_str = size_str.strip().lower()
        if size_str == 'unlimited':
            return None
            
        units = {'k': 1024, 'm': 1024**2, 'g': 1024**3, 't': 1024**4, 'p': 1024**5}
        
        try:
            if size_str[-1] in units:
                return int(float(size_str[:-1]) * units[size_str[-1]])
            return int(size_str)
        except ValueError:
            raise CommandError(f"Invalid traffic size format: {size_str}. Use format like '1G', '500M', or bytes integer.")

    def _format_bytes(self, size):
        """Format bytes into human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

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

    def _filter_radius_users(self, options):
        """Filter users based on options."""
        users = RadiusUser.objects.all()
        
        if options.get('active'):
            users = [u for u in users if u.is_active]
        elif options.get('inactive'):
            users = [u for u in users if not u.is_active]
            
        if options.get('expired'):
            users = [u for u in users if u.is_expired()]
            
        return users

    def _print_user_row(self, user):
        """Print a single user row."""
        status = 'OK'
        if not user.is_active:
            status = 'Disabled'
        elif user.is_expired():
            status = 'Expired'
        elif user.allowed_traffic is not None and user.total_traffic >= user.allowed_traffic:
            status = 'OverQuota'
        
        # Determine password display
        pwd_display = 'Encrypted'
        if user.password_hash and user.password_hash.startswith('ctp:'):
            pwd_display = user.password_hash[4:]
        
        active_sessions = user.get_active_session_count()
        expires = str(user.expiration_date.strftime('%Y-%m-%d %H:%M')) if user.expiration_date else 'Never'
        
        rx = self._format_bytes(user.rx_traffic)
        tx = self._format_bytes(user.tx_traffic)
        total = self._format_bytes(user.total_traffic)
        limit = self._format_bytes(user.allowed_traffic) if user.allowed_traffic else 'Unl.'

        remaining_str = 'Unl.'
        if user.allowed_traffic:
            remaining = user.allowed_traffic - user.total_traffic
            if remaining < 0: remaining = 0
            remaining_str = self._format_bytes(remaining)

        self.stdout.write(
            f"{user.username:<20} {pwd_display:<15} {status:<10} {expires:<16} {user.max_concurrent_sessions:<16} "
            f"{active_sessions:<18} {limit:<12} {rx:<10} {tx:<10} {total:<10} {remaining_str:<10}"
        )
