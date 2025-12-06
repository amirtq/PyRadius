from rest_framework import serializers
from .models import RadiusLog

class RadiusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = RadiusLog
        fields = '__all__'
