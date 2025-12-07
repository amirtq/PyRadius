"""
Django management command for RADIUS session management.

Usage:
    python manage.py sessions list [options]
    python manage.py sessions show <session_id>
    python manage.py sessions kick <session_id>
    python manage.py sessions cleanup [options]
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import F
from django.utils import timezone
from sessions.models import RadiusSession


class Command(BaseCommand):
    help = 'Manage RADIUS sessions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flushsessions', '-fs', action='store_true',
            help='Completely clear the sessions table'
        )

        subparsers = parser.add_subparsers(dest='action', help='Action to perform')
        
        # List sessions
        list_parser = subparsers.add_parser('list', help='List sessions')
        list_parser.add_argument(
            '--active', '-a', action='store_true',
            help='Show only active sessions'
        )
        list_parser.add_argument(
            '--stopped', '-s', action='store_true',
            help='Show only stopped sessions'
        )
        list_parser.add_argument(
            '--user', '-u', type=str, default=None,
            help='Filter by username'
        )
        list_parser.add_argument(
            '--nas', '-n', type=str, default=None,
            help='Filter by NAS identifier'
        )
        list_parser.add_argument(
            '--limit', '-l', type=int, default=50,
            help='Maximum number of sessions to show (default: 50)'
        )
        
        # Show session details
        show_parser = subparsers.add_parser('show', help='Show session details')
        show_parser.add_argument('session_id', type=str, help='Session ID to show')
        
        # Kick (terminate) session
        kick_parser = subparsers.add_parser('kick', help='Terminate a session')
        kick_parser.add_argument('session_id', type=str, help='Session ID to terminate')
        kick_parser.add_argument(
            '--force', '-f', action='store_true',
            help='Force termination without confirmation'
        )
        
        # Cleanup stale sessions
        cleanup_parser = subparsers.add_parser('cleanup', help='Cleanup stale sessions')
        cleanup_parser.add_argument(
            '--max-age', '-m', type=int, default=24,
            help='Maximum age in hours for active sessions (default: 24)'
        )
        cleanup_parser.add_argument(
            '--dry-run', '-d', action='store_true',
            help='Show what would be cleaned up without actually doing it'
        )

    def handle(self, *args, **options):
        if options.get('flushsessions'):
            self.clear_all_sessions()
            return

        action = options.get('action')
        
        if action == 'list':
            self.list_sessions(options)
        elif action == 'show':
            self.show_session(options)
        elif action == 'kick':
            self.kick_session(options)
        elif action == 'cleanup':
            self.cleanup_sessions(options)
        else:
            self.stdout.write(self.style.ERROR('Please specify an action: list, show, kick, cleanup'))

    def list_sessions(self, options):
        """List RADIUS sessions."""
        all_sessions = RadiusSession.objects.all()
        sessions = self._filter_sessions(all_sessions, options)
        
        # Manual slice
        if options['limit']:
            sessions = sessions[:options['limit']]
        
        if not sessions:
            self.stdout.write('No sessions found')
            return
        
        self._print_list_header()
        
        for session in sessions:
            self._print_session_row(session)
        
        total_count = all_sessions.count()
        shown = len(sessions)
        
        if total_count > shown:
            self.stdout.write(f"\nShowing {shown} of {total_count} session(s)")
        else:
            self.stdout.write(f"\nTotal: {total_count} session(s)")

    def show_session(self, options):
        """Show details for a session."""
        session_id = options['session_id']
        
        session = RadiusSession.find_session(session_id)
        if not session:
            raise CommandError(f'Session "{session_id}" not found')
        
        self._print_session_details(session)

    def kick_session(self, options):
        """Terminate a session."""
        session_id = options['session_id']
        force = options['force']
        
        session = RadiusSession.find_session(session_id)
        
        if not session or session.status != RadiusSession.STATUS_ACTIVE:
             # Try to find one that is active? find_session returns any.
             # If status is not active, it's not "active session found".
             raise CommandError(f'Active session "{session_id}" not found')
        
        if not force:
            self._print_session_details(session)
            confirm = input('\nAre you sure you want to terminate this session? [y/N] ')
            if confirm.lower() != 'y':
                self.stdout.write('Cancelled')
                return
        
        session.stop_session(
            terminate_cause=RadiusSession.TERMINATE_CAUSE_ADMIN_RESET
        )
        self.stdout.write(self.style.SUCCESS(f'Session "{session_id}" terminated'))

    def cleanup_sessions(self, options):
        """Cleanup stale sessions."""
        max_age = options['max_age']
        dry_run = options['dry_run']
        
        cutoff_time = timezone.now() - timezone.timedelta(hours=max_age)
        
        all_sessions = RadiusSession.objects.all()
        stale_sessions = []
        for s in all_sessions:
            if s.status == RadiusSession.STATUS_ACTIVE and s.start_time and s.start_time < cutoff_time:
                stale_sessions.append(s)
        
        count = len(stale_sessions)
        
        if count == 0:
            self.stdout.write('No stale sessions found')
            return
        
        if dry_run:
            self.stdout.write(f'Would clean up {count} stale session(s):')
            for session in stale_sessions[:10]:
                self.stdout.write(f'  - {session.session_id} ({session.username})')
            if count > 10:
                self.stdout.write(f'  ... and {count - 10} more')
        else:
            cleaned = RadiusSession.cleanup_stale_sessions(max_age_hours=max_age)
            self.stdout.write(self.style.SUCCESS(f'Cleaned up {cleaned} stale session(s)'))

    def clear_all_sessions(self):
        """Clear all sessions and reset user counters."""
        from users.models import RadiusUser

        RadiusSession.objects.all().delete()
        
        RadiusUser.objects.all().update(
            current_sessions=0,
            remaining_sessions=F('max_concurrent_sessions')
        )
        
        self.stdout.write(self.style.SUCCESS(
            "Successfully cleared all sessions and reset user counters."
        ))

    def _print_session_details(self, session):
        """Print detailed session information."""
        self.stdout.write(f"\nSession: {session.session_id}")
        self.stdout.write(f"  Username: {session.username}")
        self.stdout.write(f"  Status: {session.status}")
        self.stdout.write(f"  NAS Identifier: {session.nas_identifier}")
        self.stdout.write(f"  NAS IP Address: {session.nas_ip_address}")
        self.stdout.write(f"  Framed IP Address: {session.framed_ip_address or 'N/A'}")
        self.stdout.write(f"  Calling Station ID: {session.calling_station_id or 'N/A'}")
        self.stdout.write(f"  Start Time: {session.start_time}")
        if session.last_updated:
            self.stdout.write(f"  Last Updated: {session.last_updated}")
        if session.stop_time:
            self.stdout.write(f"  Stop Time: {session.stop_time}")
        self.stdout.write(f"  Session Time: {self._format_duration(session.session_time)}")
        self.stdout.write(f"  Input: {self._format_bytes(session.input_octets)} "
                         f"({session.input_packets} packets)")
        self.stdout.write(f"  Output: {self._format_bytes(session.output_octets)} "
                         f"({session.output_packets} packets)")
        if session.terminate_cause:
            self.stdout.write(f"  Terminate Cause: {session.terminate_cause}")

    def _format_duration(self, seconds):
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{hours}h {minutes}m"

    def _format_bytes(self, bytes_count):
        """Format bytes in human-readable format."""
        if bytes_count < 1024:
            return f"{bytes_count} B"
        elif bytes_count < 1024 * 1024:
            return f"{bytes_count / 1024:.1f} KB"
        elif bytes_count < 1024 * 1024 * 1024:
            return f"{bytes_count / (1024 * 1024):.1f} MB"
        else:
            return f"{bytes_count / (1024 * 1024 * 1024):.1f} GB"

    def _filter_sessions(self, sessions, options):
        """Filter sessions based on options."""
        if options['active']:
            sessions = [s for s in sessions if s.status == RadiusSession.STATUS_ACTIVE]
        elif options['stopped']:
            sessions = [s for s in sessions if s.status == RadiusSession.STATUS_STOPPED]
        
        if options['user']:
            sessions = [s for s in sessions if s.username == options['user']]
        
        if options['nas']:
            sessions = [s for s in sessions if s.nas_identifier == options['nas']]
            
        return sessions

    def _print_list_header(self):
        """Print the header for session list."""
        self.stdout.write(
            f"{'Session ID':<20} {'Username':<15} {'Client IP':<15} {'MAC':<17} "
            f"{'NAS':<10} {'Status':<10} {'In':<10} {'Out':<10} {'Started':<20} {'Last Updated':<20}"
        )
        self.stdout.write("-" * 150)

    def _print_session_row(self, session):
        """Print a single session row."""
        if session.start_time:
            started = session.start_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            started = 'N/A'
            
        if session.last_updated:
            last_upd = session.last_updated.strftime('%Y-%m-%d %H:%M:%S')
        else:
            last_upd = 'N/A'
        
        sid = str(session.session_id or 'N/A')
        username = str(session.username or 'N/A')
        client_ip = str(session.framed_ip_address or 'N/A')
        mac = str(session.calling_station_id or 'N/A')
        nas = str(session.nas_identifier or '')
        
        input_data = self._format_bytes(session.input_octets)
        output_data = self._format_bytes(session.output_octets)

        self.stdout.write(
            f"{sid[:20]:<20} {username:<15} {client_ip:<15} {mac[:17]:<17} "
            f"{nas[:10]:<10} {session.status:<10} "
            f"{input_data:<10} {output_data:<10} {started:<20} {last_upd:<20}"
        )
