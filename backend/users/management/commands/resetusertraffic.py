from django.core.management.base import BaseCommand, CommandError
from users.models import RadiusUser

class Command(BaseCommand):
    help = 'Clear used traffic for a single user or all users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user', '-u',
            type=str,
            help='Username to clear traffic for. If not provided, clears for ALL users (with confirmation).'
        )
        parser.add_argument(
            '--force', '-f',
            action='store_true',
            help='Force clearing implementation without confirmation (only applies when clearing all users)'
        )

    def handle(self, *args, **options):
        username = options.get('user')
        force = options.get('force')

        if username:
            try:
                user = RadiusUser.objects.get(username=username)
                user.rx_traffic = 0
                user.tx_traffic = 0
                user.total_traffic = 0
                user.save()
                self.stdout.write(self.style.SUCCESS(f'Successfully cleared traffic for user "{username}"'))
            except RadiusUser.DoesNotExist:
                raise CommandError(f'User "{username}" not found')
        else:
            if not force:
                confirm = input('Are you sure you want to clear traffic for ALL users? [y/N] ')
                if confirm.lower() != 'y':
                    self.stdout.write('Cancelled')
                    return
            
            # Use update for efficiency
            count = RadiusUser.objects.all().update(rx_traffic=0, tx_traffic=0, total_traffic=0)
            self.stdout.write(self.style.SUCCESS(f'Successfully cleared traffic for {count} users'))
