from django.contrib.staticfiles.apps import \
    StaticFilesConfig as _StaticFilesConfig
from django.contrib.staticfiles.storage import CachedStaticFilesStorage

from pipeline.storage import GZIPMixin


class StaticFilesConfig(_StaticFilesConfig):
    ignore_patterns = ['CVS', '.*', '*~', 'src', '*.map', '_builds']


class PipelineCachedGZIPedStorage(GZIPMixin, CachedStaticFilesStorage):
    gzip_patterns = ("*.css", "*.js")
