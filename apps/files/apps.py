from django.contrib.staticfiles.apps import StaticFilesConfig as _StaticFilesConfig


class StaticFilesConfig(_StaticFilesConfig):
    ignore_patterns = ['CVS', '.*', '*~', 'src', '*.map', '_builds']
