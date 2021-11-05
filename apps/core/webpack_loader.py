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


class TestingWebpackLoader(WebpackLoader):
    def get_bundle(self, bundle_name):
        """
        Mocks `render_bundle` template tag to avoid WebpackBundleLookupError
        on running tests.

        The name and URL don't matter, the file doesn't need to exist.
        """
        return [{'name': 'test.bundle.js', 'url': 'https://localhost:8000/static/bundles/test.bundle.js'}]
