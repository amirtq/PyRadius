from rest_framework import viewsets, filters 
from .serializers import AdminUserSerializer, RadiusUserSerializer
from rest_framework.permissions import IsAuthenticated
from .models import AdminUser, RadiusUser

class RadiusUserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows RADIUS Users to be viewed or edited.
    """
    queryset = RadiusUser.objects.all()
    serializer_class = RadiusUserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['username', 'notes']
    filterset_fields = ['is_active']

class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = AdminUser.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated]
