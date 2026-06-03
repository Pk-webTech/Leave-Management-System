from django.apps import AppConfig


class LeaveappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'leaveapp'

    def ready(self):
        import leaveapp.signals  # noqa: F401