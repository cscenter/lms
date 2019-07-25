from django.apps import AppConfig


class ProjectConfig(AppConfig):
    name = 'compsciclub_ru'

    def ready(self):
        from . import permissions
