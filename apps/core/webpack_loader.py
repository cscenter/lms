from webpack_loader.loader import WebpackLoader

from django.contrib.staticfiles.storage import staticfiles_storage


class BundleDirectoryWebpackLoader(WebpackLoader):
    """
    Returns chunk url relative to the bundle directory ignoring public path.
    """
    def get_chunk_url(self, chunk):
        rel_path = '{0}{1}'.format(self.config['BUNDLE_DIR_NAME'],
                                   chunk['name'])
        return staticfiles_storage.url(rel_path)
