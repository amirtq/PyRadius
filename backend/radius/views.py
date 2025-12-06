from rest_framework import viewsets, permissions, filters
from .models import RadiusLog
from .serializers import RadiusLogSerializer

class RadiusLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Radius Logs to be viewed.
    """
    queryset = RadiusLog.objects.all().order_by('-timestamp')
    serializer_class = RadiusLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['message', 'level', 'logger']
