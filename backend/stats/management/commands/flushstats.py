from django.core.management.base import BaseCommand
from stats.models import (
    StatsServerActiveSessions,
    StatsServerTotalTraffic,
    StatsUsersActiveSessions,
    StatsUsersTotalTraffic
)

class Command(BaseCommand):
    help = 'Flush all statistics data (Server and User history)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Flushing all statistics data...'))
        
        # Note: delete() returns (total_deleted, {model_name: count})
        count_server_sessions = StatsServerActiveSessions.objects.all().delete()[0]
        count_server_traffic = StatsServerTotalTraffic.objects.all().delete()[0]
        count_user_sessions = StatsUsersActiveSessions.objects.all().delete()[0]
        count_user_traffic = StatsUsersTotalTraffic.objects.all().delete()[0]
        
        total = count_server_sessions + count_server_traffic + count_user_sessions + count_user_traffic
        
        self.stdout.write(self.style.SUCCESS(f'Successfully flushed {total} statistics records'))
