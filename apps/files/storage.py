import os
import posixpath
import re
from urllib.parse import unquote, urldefrag

from django.conf import settings
from django.contrib.staticfiles.storage import ManifestStaticFilesStorage
from django.core.files.storage import get_storage_class, FileSystemStorage
from django.utils.functional import LazyObject
from static_compress import CompressedManifestStaticFilesStorage, compressors
from storages.backends.s3boto3 import S3Boto3Storage


# Static files
class FixedCompressedManifestStaticFilesStorage(CompressedManifestStaticFilesStorage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed_extensions = ['css', 'js', 'svg']
        self.keep_original = True
        self.minimum_kb = 30
        self.compressors = [compressors.ZlibCompressor()]

    def _get_dest_path(self, path):
        return self.stored_name(path)


class CloudFrontManifestStaticFilesStorage(ManifestStaticFilesStorage):
    """
    All static files are collected to the `settings.STATIC_ROOT` directory
    and available by `/static/` URL prefix on production.
    Usually it means that `settings.STATIC_URL` points to the `/static/` but
    Cloudfront is configured to work with alternate domain name
    (e.g. https://cdn.example.com/) and this is the actual value of
    `settings.STATIC_URL`. As a side-effect `collectstatic` post-processing
    skips (in *.css files) absolutely all `url(...)` patterns starting
    with prefix `/static/`.
    This class should fix this problem by customizing `url_converter` -
    instead of checking `settings.STATIC_URL` (that points to the cdn
    subdomain) it checks `settings.CDN_SOURCE_STATIC_URL` that points to
    the `/static/` value. As a result all urls starting with
    `settings.CDN_SOURCE_STATIC_URL` will be modified to point to the
    `settings.STATIC_URL` cdn domain.
    """
    def url_converter(self, name, hashed_files, template=None):
        """
        Return the custom URL converter for the given file name.
        """
        if template is None:
            template = self.default_template

        def converter(matchobj):
            """
            Convert the matched URL to a normalized and hashed URL.

            This requires figuring out which files the matched URL resolves
            to and calling the url() method of the storage.
            """
            matched, url = matchobj.groups()

            # Ignore absolute/protocol-relative and data-uri URLs.
            if re.match(r'^[a-z]+:', url):
                return matched

            # Ignore absolute URLs that don't point to a static file (dynamic
            # CSS / JS?). Note that STATIC_URL cannot be empty.
            if url.startswith('/') and not url.startswith(settings.CDN_SOURCE_STATIC_URL):
                return matched

            # Strip off the fragment so a path-like fragment won't interfere.
            url_path, fragment = urldefrag(url)


            if url_path.startswith('/'):
                # Otherwise the condition above would have returned prematurely.
                assert url_path.startswith(settings.CDN_SOURCE_STATIC_URL)
                target_name = url_path[len(settings.CDN_SOURCE_STATIC_URL):]
            else:
                # We're using the posixpath module to mix paths and URLs conveniently.
                source_name = name if os.sep == '/' else name.replace(os.sep, '/')
                target_name = posixpath.join(posixpath.dirname(source_name), url_path)

            # Determine the hashed name of the target file with the storage backend.
            hashed_url = self._url(
                self._stored_name, unquote(target_name),
                force=True, hashed_files=hashed_files,
            )

            transformed_url = '/'.join(url_path.split('/')[:-1] + hashed_url.split('/')[-1:])

            if transformed_url.startswith('/'):
                # Otherwise the condition above would have returned prematurely.
                assert transformed_url.startswith(settings.CDN_SOURCE_STATIC_URL)
                transformed_url = settings.STATIC_URL + transformed_url[len(settings.CDN_SOURCE_STATIC_URL):]

            # Restore the fragment that was stripped off earlier.
            if fragment:
                transformed_url += ('?#' if '?#' in url else '#') + fragment

            # Return the hashed version to the file
            return template % unquote(transformed_url)

        return converter


# Uploaded files


# XXX: Private files are stored under public directory and protected by
# nginx `internal` directive.
class PrivateFileSystemStorage(FileSystemStorage):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._location = self._value_or_setting(self._location,
                                                settings.PRIVATE_MEDIA_ROOT)
        self._base_url = self._value_or_setting(self._base_url,
                                                settings.PRIVATE_MEDIA_URL)


class PublicMediaS3Storage(S3Boto3Storage):
    location = getattr(settings, 'AWS_PUBLIC_MEDIA_LOCATION', 'media')
    file_overwrite = False
    default_acl = 'public-read'
    url_protocol = 'https:'


class PrivateMediaS3Storage(S3Boto3Storage):
    location = getattr(settings, 'AWS_PRIVATE_MEDIA_LOCATION', 'private')
    file_overwrite = False
    default_acl = 'private'
    url_protocol = 'https:'
    custom_domain = False
    querystring_expire = 10  # in seconds


class PrivateFilesStorage(LazyObject):
    def _setup(self):
        import_path = settings.PRIVATE_FILE_STORAGE
        self._wrapped = get_storage_class(import_path=import_path)()


private_storage = PrivateFilesStorage()
