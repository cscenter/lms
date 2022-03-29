import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from .base import *

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

# XXX: Enable AWS SES backend on CS Center and CS Club, then remove this setting
EMAIL_BACKEND = 'django_ses.SESBackend'
