from django.apps import AppConfig


class ContestsConfig(AppConfig):
    name = 'contests'

    def ready(self):
        from . import signals
