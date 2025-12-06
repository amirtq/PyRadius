from rest_framework import viewsets, permissions, filters
from .models import RadiusSession
from .serializers import RadiusSessionSerializer

class RadiusSessionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows Radius Sessions to be viewed.
    """
    queryset = RadiusSession.objects.all().order_by('-start_time')
    serializer_class = RadiusSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'session_id', 'nas_ip_address', 'calling_station_id']
    filterset_fields = ['status', 'nas_identifier']
