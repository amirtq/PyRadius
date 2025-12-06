from django.core.management.base import BaseCommand
from users.models import AdminUser

class Command(BaseCommand):
    help = 'Lists all admin users'

    def handle(self, *args, **options):
        admin_users = AdminUser.objects.filter(is_superuser=True)
        
        if not admin_users.exists():
            self.stdout.write(self.style.WARNING('No admin users found.'))
            return

        self.stdout.write(self.style.SUCCESS(f'Found {admin_users.count()} admin user(s):'))
        self.stdout.write(f"{'ID':<5} {'Username':<20} {'Is Staff':<10} {'Is Active':<10}")
        self.stdout.write("-" * 50)
        
        for user in admin_users:
            self.stdout.write(f"{user.pk:<5} {user.username:<20} {str(user.is_staff):<10} {str(user.is_active):<10}")
