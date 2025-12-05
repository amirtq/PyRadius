from django.core.management.base import BaseCommand
from radius.models import RadiusLog

class Command(BaseCommand):
    help = 'Show radius logs'

    def add_arguments(self, parser):
        parser.add_argument(
            '-n', '--lines',
            type=int,
            default=50,
            help='Number of lines to show (default: 50)',
        )
        parser.add_argument(
            '-f', '--filter',
            type=str,
            default=None,
            help='Filter logs by string matching (case-insensitive)',
        )
        parser.add_argument(
            '-fl', '--flushlogs',
            action='store_true',
            help='Clear all logs',
        )

    def handle(self, *args, **options):
        if options['flushlogs']:
            self.stdout.write('Flushing all logs...')
            count, _ = RadiusLog.objects.all().delete()
            self.stdout.write(self.style.SUCCESS(f'Successfully deleted {count} logs.'))
            return

        logs = RadiusLog.objects.all()

        if options['filter']:
            logs = logs.filter(message__icontains=options['filter'])

        # Get the last N logs. 
        # Default ordering is -timestamp (newest first).
        limit = options['lines']
        logs = logs[:limit]

        # Convert to list and reverse to show oldest first (chronological) so it reads like a log file
        logs_list = list(logs)
        logs_list.reverse()

        for log in logs_list:
            timestamp_str = log.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            
            level_display = log.level
            if log.level == 'ERROR' or log.level == 'CRITICAL':
                level_display = self.style.ERROR(log.level)
            elif log.level == 'WARNING':
                level_display = self.style.WARNING(log.level)
            elif log.level == 'INFO':
                level_display = self.style.SUCCESS(log.level)
            
            self.stdout.write(f"[{timestamp_str}] {level_display} [{log.logger}] {log.message}")
