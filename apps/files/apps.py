from django.apps import AppConfig
from django.contrib.staticfiles.apps import StaticFilesConfig as _StaticFilesConfig


class StaticFilesConfig(_StaticFilesConfig):
    ignore_patterns = ['CVS', '.*', '*~', 'src', '*.map', '_builds']


class MediaFilesConfig(AppConfig):
    name = 'files'
    label = 'media'
