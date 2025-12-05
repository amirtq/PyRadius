from django.apps import AppConfig


class SessionsConfig(AppConfig):
    name = 'sessions'
    label = 'radius_sessions'  # Unique label to avoid conflict with django.contrib.sessions
    verbose_name = 'RADIUS Sessions'
