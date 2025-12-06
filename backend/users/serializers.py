from rest_framework import serializers
from .models import AdminUser

class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = AdminUser
        fields = ('id', 'username', 'password', 'token', 'is_active', 'last_login', 'created_at')
        read_only_fields = ('id', 'last_login', 'created_at')

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = AdminUser(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance
