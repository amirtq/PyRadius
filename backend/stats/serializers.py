from rest_framework import serializers
from stats.models import (
    StatsServerActiveSessions,
    StatsServerTotalTraffic,
    StatsUsersActiveSessions,
    StatsUsersTotalTraffic,
)

class StatsServerActiveSessionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatsServerActiveSessions
        fields = '__all__'

class StatsServerTotalTrafficSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatsServerTotalTraffic
        fields = '__all__'

class StatsUsersActiveSessionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatsUsersActiveSessions
        fields = '__all__'

class StatsUsersTotalTrafficSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatsUsersTotalTraffic
        fields = '__all__'
