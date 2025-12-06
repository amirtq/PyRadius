from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import AdminUser
from .serializers import AdminUserSerializer

class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = AdminUser.objects.all()
    serializer_class = AdminUserSerializer
    permission_classes = [IsAuthenticated]
