"""
Statistics App Configuration
"""

from django.apps import AppConfig


class StatsConfig(AppConfig):
    """
    Django app configuration for the statistics module.
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'stats'
    verbose_name = 'Statistics'
