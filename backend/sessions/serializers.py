from rest_framework import serializers
from .models import RadiusSession

class RadiusSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RadiusSession
        fields = '__all__'
