from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import RadiusLog
from .serializers import RadiusLogSerializer

class RadiusLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Radius Logs to be viewed.
    """
    queryset = RadiusLog.objects.all().order_by('-timestamp')
    serializer_class = RadiusLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['message', 'level', 'logger']
    filterset_fields = ['level']
