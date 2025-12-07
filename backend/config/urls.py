from django.urls import path, include, re_path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from users.views import AdminUserViewSet, RadiusUserViewSet
from nas.views import NASClientViewSet
from sessions.views import RadiusSessionViewSet
from radius.views import RadiusLogViewSet
from stats.views import (
    StatsServerActiveSessionsViewSet,
    StatsServerTotalTrafficViewSet,
    StatsUsersActiveSessionsViewSet,
    StatsUsersTotalTrafficViewSet,
)
from stats.overview_views import UserStatusCountsView, LogSeverityCountsView

router = DefaultRouter()
router.register(r'admins', AdminUserViewSet)
router.register(r'radius-users', RadiusUserViewSet)
router.register(r'nas', NASClientViewSet)
router.register(r'sessions', RadiusSessionViewSet)
router.register(r'logs', RadiusLogViewSet)
router.register(r'stats/server/sessions', StatsServerActiveSessionsViewSet)
router.register(r'stats/server/traffic', StatsServerTotalTrafficViewSet)
router.register(r'stats/users/sessions', StatsUsersActiveSessionsViewSet)
router.register(r'stats/users/traffic', StatsUsersTotalTrafficViewSet)

urlpatterns = [
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/stats/users/status-counts/', UserStatusCountsView.as_view(), name='user_status_counts'),
    path('api/stats/server/logs/counts/', LogSeverityCountsView.as_view(), name='log_counts'),
    path('api/', include(router.urls)),
    # Catch-all for React frontend
    re_path(r'^.*$', TemplateView.as_view(template_name='index.html')),
]
