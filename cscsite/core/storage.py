from django.contrib.staticfiles.storage import CachedStaticFilesStorage

from pipeline.storage import GZIPMixin


class PipelineCachedGZIPedStorage(GZIPMixin, CachedStaticFilesStorage):
    gzip_patterns = ("css/*.css", "js/*.js")
