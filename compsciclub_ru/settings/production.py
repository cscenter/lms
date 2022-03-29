import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from .base import *

# Sentry
SENTRY_DSN = env("SENTRY_DSN")
SENTRY_LOG_LEVEL = env.int("SENTRY_LOG_LEVEL", default=logging.INFO)

sentry_logging = LoggingIntegration(
    level=logging.INFO,        # Capture info and above as breadcrumbs
    event_level=logging.ERROR  # Send errors as events
)

sentry_sdk.init(
    dsn=SENTRY_DSN,
    integrations=[sentry_logging, DjangoIntegration()]
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/tmp/django_cache_club'
    }
}

# Remove this setting? cs club is configured for AWS SES
POST_OFFICE['BACKENDS']['ses'] = EMAIL_BACKEND
