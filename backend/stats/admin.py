"""
Statistics Admin Configuration

This module registers the statistics models with Django admin
for easy viewing and management.
"""

from django.contrib import admin
from stats.models import (
    StatsServerActiveSessions,
    StatsServerTotalTraffic,
    StatsUsersActiveSessions,
    StatsUsersTotalTraffic,
)


@admin.register(StatsServerActiveSessions)
class StatsServerActiveSessionsAdmin(admin.ModelAdmin):
    """Admin configuration for server active sessions stats."""
    list_display = ('timestamp', 'active_sessions')
    list_filter = ('timestamp',)
    ordering = ('-timestamp',)
    readonly_fields = ('timestamp', 'active_sessions')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(StatsServerTotalTraffic)
class StatsServerTotalTrafficAdmin(admin.ModelAdmin):
    """Admin configuration for server total traffic stats."""
    list_display = ('timestamp', 'total_rx', 'total_tx', 'total_traffic')
    list_filter = ('timestamp',)
    ordering = ('-timestamp',)
    readonly_fields = ('timestamp', 'total_rx', 'total_tx', 'total_traffic')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(StatsUsersActiveSessions)
class StatsUsersActiveSessionsAdmin(admin.ModelAdmin):
    """Admin configuration for user active sessions stats."""
    list_display = ('timestamp', 'username', 'active_sessions')
    list_filter = ('timestamp', 'username')
    search_fields = ('username',)
    ordering = ('-timestamp',)
    readonly_fields = ('timestamp', 'username', 'active_sessions')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(StatsUsersTotalTraffic)
class StatsUsersTotalTrafficAdmin(admin.ModelAdmin):
    """Admin configuration for user total traffic stats."""
    list_display = ('timestamp', 'username', 'rx_traffic', 'tx_traffic', 'total_traffic')
    list_filter = ('timestamp', 'username')
    search_fields = ('username',)
    ordering = ('-timestamp',)
    readonly_fields = ('timestamp', 'username', 'rx_traffic', 'tx_traffic', 'total_traffic')
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
