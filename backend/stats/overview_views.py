from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users.models import RadiusUser
from radius.models import RadiusLog
from django.utils import timezone
from django.db.models import Q, F, Count

class UserStatusCountsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()
        
        # 1. Inactive (Disabled)
        inactive_count = RadiusUser.objects.filter(is_active=False).count()
        
        # 2. Expired (Active but past expiration)
        expired_count = RadiusUser.objects.filter(
            is_active=True, 
            expiration_date__lt=now
        ).count()
        
        # 3. OverQuota (Active, Not Expired, but over traffic limit)
        # We assume Expired takes precedence over OverQuota as per model logic
        overquota_count = RadiusUser.objects.filter(
            is_active=True
        ).exclude(
            expiration_date__lt=now
        ).filter(
            allowed_traffic__isnull=False,
            total_traffic__gte=F('allowed_traffic')
        ).count()
        
        # 4. Active (The rest: Active, Not Expired, Not OverQuota)
        active_count = RadiusUser.objects.filter(
            is_active=True
        ).exclude(
            expiration_date__lt=now
        ).exclude(
            allowed_traffic__isnull=False,
            total_traffic__gte=F('allowed_traffic')
        ).count()
        
        data = [
            {'name': 'Active', 'value': active_count, 'color': '#10b981'}, # Emerald 500
            {'name': 'Inactive', 'value': inactive_count, 'color': '#64748b'}, # Slate 500
            {'name': 'Expired', 'value': expired_count, 'color': '#f59e0b'}, # Amber 500
            {'name': 'Overquota', 'value': overquota_count, 'color': '#ef4444'}, # Red 500
        ]
        
        return Response(data)

class LogSeverityCountsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = RadiusLog.objects.all()
        
        # Apply filters manually since we aren't using a FilterSet here
        # Frontend sends timestamp__gte
        timestamp_gte = request.query_params.get('timestamp__gte')
        if timestamp_gte:
            qs = qs.filter(timestamp__gte=timestamp_gte)
            
        timestamp_lte = request.query_params.get('timestamp__lte')
        if timestamp_lte:
            qs = qs.filter(timestamp__lte=timestamp_lte)
            
        data = qs.values('level').annotate(value=Count('id'))
        
        colors = {
            'INFO': '#3b82f6', # Blue
            'WARNING': '#f59e0b', # Amber
            'ERROR': '#ef4444', # Red
            'CRITICAL': '#b91c1c', # Dark Red
            'DEBUG': '#94a3b8', # Gray
        }
        
        formatted_data = []
        for item in data:
            lvl = item['level']
            formatted_data.append({
                'name': lvl,
                'value': item['value'],
                'color': colors.get(lvl, '#cbd5e1')
            })
            
        return Response(formatted_data)
