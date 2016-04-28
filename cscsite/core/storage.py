from django.contrib.staticfiles.storage import CachedStaticFilesStorage

from pipeline.storage import GZIPMixin, PipelineMixin


class PipelineCachedGZIPedStorage(PipelineMixin, GZIPMixin,
                                  CachedStaticFilesStorage):
    pass
