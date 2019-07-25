# -*- coding: utf-8 -*-

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from .base import *

DEBUG = False
for template in TEMPLATES:
    template['OPTIONS']['debug'] = DEBUG

ALLOWED_HOSTS = [".compsciclub.ru"]
DEFAULT_URL_SCHEME = 'https'  # default scheme for `core.urls.reverse`

MEDIA_ROOT = str(Path('/shared', 'media'))

# Logging-related stuff
sentry_sdk.init(
    dsn="https://f2a254aefeae4aeaa09657771205672f@sentry.io/13763",
    integrations=[DjangoIntegration()]
)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/tmp/django_cache_club'
    }
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        'django.db.backends': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': False,
        },
        'django.request': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': True,
        },
        'django.template': {
            'level': 'ERROR',
            'handlers': ['console'],
            'propagate': True,
        },
        "rq.worker": {
            "level": "WARNING",
            "handlers": ["console"],
            'propagate': False,
        },
    },
}

EMAIL_HOST_PASSWORD = 'XgpWN4CzBGqCbNsb8'

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# -- learning
SLIDESHARE_API_KEY = "E3GDS7t4"
SLIDESHARE_SECRET = "fnk6fOLp"
SLIDESHARE_USERNAME = "compscicenter"
SLIDESHARE_PASSWORD = "vorobey"

YANDEX_DISK_USERNAME = "csc-slides@yandex.ru"
YANDEX_DISK_PASSWORD = "deelthisat"


# django-dbbackup settings
DBBACKUP_CLEANUP_KEEP = 30
DBBACKUP_CLEANUP_KEEP_MEDIA = 30
CSC_TMP_BACKUP_DIR = "/tmp/csclub_backup"
DBBACKUP_BACKUP_DIRECTORY = CSC_TMP_BACKUP_DIR

DBBACKUP_S3_BUCKET = 'csclub'
DBBACKUP_S3_DIRECTORY = 'cscweb_backups'
DBBACKUP_S3_DOMAIN = 's3.eu-central-1.amazonaws.com'
# Access Key for csclub backup user
DBBACKUP_S3_ACCESS_KEY = 'AKIAJWPKEDQ6YJEPKFFQ'
DBBACKUP_S3_SECRET_KEY = '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'

NEWRELIC_ENV = 'production'

REDIS_PASSWORD = '3MUvZ/wV{6e86jq@x4uA%RDn9KbrV#WU]A=L76J@Q9iCa*9+vN'
THUMBNAIL_REDIS_PASSWORD = REDIS_PASSWORD
for queue in RQ_QUEUES.values():
    if 'PASSWORD' in queue:
        queue['PASSWORD'] = REDIS_PASSWORD


# Recaptcha settings
RECAPTCHA_PUBLIC_KEY = '6Lc_7AsTAAAAAOoC9MhVSoJ6O-vILaGgDEgtLBty'
RECAPTCHA_PRIVATE_KEY = '6Lc_7AsTAAAAAJeq5ZzlUQC471py3sq404u8DYqr'
