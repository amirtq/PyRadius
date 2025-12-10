"""
Scheduler App Configuration
"""

from django.apps import AppConfig


class SchedulerConfig(AppConfig):
    """Configuration for the Scheduler app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'scheduler'
    verbose_name = 'Task Scheduler'
