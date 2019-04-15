from django.contrib.staticfiles.apps import \
    StaticFilesConfig as _StaticFilesConfig
from django.contrib.staticfiles.storage import ManifestStaticFilesStorage

from pipeline.storage import GZIPMixin


class StaticFilesConfig(_StaticFilesConfig):
    ignore_patterns = ['CVS', '.*', '*~', 'src', '*.map', '_builds']


class PipelineCachedGZIPedStorage(GZIPMixin, ManifestStaticFilesStorage):
    gzip_patterns = ("*.css", "*.js")
