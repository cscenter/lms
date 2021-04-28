from django.apps import AppConfig


class ContestsConfig(AppConfig):
    name = 'grading'

    def ready(self):
        from . import signals  # pylint: disable=unused-import
