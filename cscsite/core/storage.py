from django.contrib.staticfiles.storage import CachedStaticFilesStorage

from pipeline.storage import GZIPMixin


class PipelineCachedGZIPedStorage(GZIPMixin, CachedStaticFilesStorage):
    pass
