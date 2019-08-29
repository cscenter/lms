from django.contrib.staticfiles.apps import \
    StaticFilesConfig as _StaticFilesConfig
from django.contrib.staticfiles.storage import ManifestStaticFilesStorage

from static_compress import CompressMixin


class StaticFilesConfig(_StaticFilesConfig):
    ignore_patterns = ['CVS', '.*', '*~', 'src', '*.map', '_builds']


class PipelineCachedGZIPedStorage(CompressMixin, ManifestStaticFilesStorage):
    pass
