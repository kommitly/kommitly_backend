from django.apps import AppConfig


class GoalsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'goals'

    def ready(self):
        # Import your signals.py file here to register the receivers
        import goals.signals
