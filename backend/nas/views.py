from rest_framework import viewsets, permissions
from .models import NASClient
from .serializers import NASClientSerializer

class NASClientViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows NAS Clients to be viewed or edited.
    """
    queryset = NASClient.objects.all()
    serializer_class = NASClientSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['identifier', 'ip_address', 'description']
    filterset_fields = ['is_active']
