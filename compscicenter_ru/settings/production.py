import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from .base import *

# STATICFILES_STORAGE = 'files.storage.CloudFrontManifestStaticFilesStorage'
CDN_SOURCE_STATIC_URL = STATIC_URL
# CDN_STATIC_URL = 'https://resources.compscicenter.ru/'
# STATIC_URL = CDN_STATIC_URL
# for webpack_config in WEBPACK_LOADER.values():
#    webpack_config['LOADER_CLASS'] = 'core.webpack_loader.BundleDirectoryWebpackLoader'

# Sentry
sentry_logging = LoggingIntegration(
    level=logging.INFO,        # Capture info and above as breadcrumbs
    event_level=logging.ERROR  # Send errors as events
)
sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=[sentry_logging, DjangoIntegration()]
)


CACHES['default'] = {
    'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
    'LOCATION': '/tmp/django_cache'
}
