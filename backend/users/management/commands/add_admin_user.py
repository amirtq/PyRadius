from django.contrib.auth.management.commands.createsuperuser import Command as BaseCommand

class Command(BaseCommand):
    help = 'Used to create an admin user.'
