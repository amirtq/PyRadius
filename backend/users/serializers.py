from rest_framework import serializers
from .models import AdminUser, RadiusUser

class RadiusUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    use_cleartext_password = serializers.BooleanField(write_only=True, required=False, default=False)
    status = serializers.CharField(source='status_label', read_only=True)

    class Meta:
        model = RadiusUser
        fields = (
            'id', 'username', 'password', 'use_cleartext_password', 'max_concurrent_sessions',
            'expiration_date', 'is_active', 'status', 'notes',
            'rx_traffic', 'tx_traffic', 'total_traffic',
            'allowed_traffic', 'current_sessions', 'remaining_sessions',
            'created_at', 'updated_at'
        )
        read_only_fields = (
            'id', 'created_at', 'updated_at', 
            'rx_traffic', 'tx_traffic', 'total_traffic', 
            'current_sessions', 'remaining_sessions'
        )

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        use_cleartext = validated_data.pop('use_cleartext_password', False)
        user = RadiusUser(**validated_data)
        if password:
            user.set_password(password, use_cleartext=use_cleartext)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        use_cleartext = validated_data.pop('use_cleartext_password', False)
        
        # Helper to avoid error if set_password called
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        if password:
            instance.set_password(password, use_cleartext=use_cleartext)
            
        instance.save()
        return instance

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
