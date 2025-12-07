from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import timedelta
from sessions.models import RadiusSession
from stats.models import (
    StatsServerActiveSessions,
    StatsServerTotalTraffic,
    StatsUsersActiveSessions,
    StatsUsersTotalTraffic,
)
from stats.serializers import (
    StatsServerActiveSessionsSerializer,
    StatsServerTotalTrafficSerializer,
    StatsUsersActiveSessionsSerializer,
    StatsUsersTotalTrafficSerializer,
)

class BaseStatsViewSet(viewsets.ReadOnlyModelViewSet):
    """Base ViewSet for stats with common filtering logic."""
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_fields = {'timestamp': ['gte', 'lte', 'exact', 'gt', 'lt']}

    def get_queryset(self):
        queryset = super().get_queryset()
        # Default to last 24 hours if no filtering provided for timestamp
        # This prevents loading massive amounts of data by default
        if not self.request.query_params.get('timestamp__gte'):
            last_24h = timezone.now() - timedelta(hours=24)
            queryset = queryset.filter(timestamp__gte=last_24h)
        return queryset

class StatsServerActiveSessionsViewSet(BaseStatsViewSet):
    queryset = StatsServerActiveSessions.objects.all()
    serializer_class = StatsServerActiveSessionsSerializer
    filterset_fields = {'timestamp': ['gte', 'lte']}

    @action(detail=False, methods=['get'])
    def current(self, request):
        count = RadiusSession.objects.filter(status=RadiusSession.STATUS_ACTIVE).count()
        return Response({'active_sessions': count})

class StatsServerTotalTrafficViewSet(BaseStatsViewSet):
    queryset = StatsServerTotalTraffic.objects.all()
    serializer_class = StatsServerTotalTrafficSerializer
    filterset_fields = {'timestamp': ['gte', 'lte']}

class StatsUsersActiveSessionsViewSet(BaseStatsViewSet):
    queryset = StatsUsersActiveSessions.objects.all()
    serializer_class = StatsUsersActiveSessionsSerializer
    filterset_fields = {
        'timestamp': ['gte', 'lte'],
        'username': ['exact', 'icontains']
    }

class StatsUsersTotalTrafficViewSet(BaseStatsViewSet):
    queryset = StatsUsersTotalTraffic.objects.all()
    serializer_class = StatsUsersTotalTrafficSerializer
    filterset_fields = {
        'timestamp': ['gte', 'lte'],
        'username': ['exact', 'icontains']
    }
