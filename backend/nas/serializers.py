from rest_framework import serializers
from .models import NASClient

class NASClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = NASClient
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
