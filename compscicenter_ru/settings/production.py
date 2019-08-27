# -*- coding: utf-8 -*-

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

from .base import *

DEBUG = False
for template in TEMPLATES:
    template['OPTIONS']['debug'] = DEBUG

ALLOWED_HOSTS = [".compscicenter.ru"]
DEFAULT_URL_SCHEME = 'https'  # default scheme for `core.urls.reverse`

MEDIA_ROOT = str(Path('/shared', 'media'))

# Logging-related stuff
sentry_sdk.init(
    dsn="https://f2a254aefeae4aeaa09657771205672f@sentry.io/13763",
    integrations=[DjangoIntegration()]
)

CACHES['default'] = {
    'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
    'LOCATION': '/tmp/django_cache'
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
        "rq.worker": {
            "level": "WARNING",
            "handlers": ["console"],
            'propagate': False,
        },
        "post_office": {
            "level": "ERROR",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}

EMAIL_HOST_PASSWORD = 'P@ssw0rd238'

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = None
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_DOMAIN = '.compscicenter.ru'


# -- learning
SLIDESHARE_API_KEY = "E3GDS7t4"
SLIDESHARE_SECRET = "fnk6fOLp"
SLIDESHARE_USERNAME = "compscicenter"
SLIDESHARE_PASSWORD = "vorobey"

YANDEX_DISK_USERNAME = "csc-slides@yandex.ru"
YANDEX_DISK_PASSWORD = "deelthisat"


# django-dbbackup settings
DBBACKUP_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
DBBACKUP_STORAGE_OPTIONS = {
    'location': '',
    'bucket_name': 'cscenter',
    'region_name': 'eu-central-1',
    'access_key': 'AKIAJMQIFB2CNXR65ALQ',
    'secret_key': '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',
    'default_acl': None,
}
DBBACKUP_TMP_DIR = '/shared/backup_tmp'
DBBACKUP_DATE_FORMAT = '%d-%m-%Y-%H'
DBBACKUP_FILENAME_TEMPLATE = 'backups/{servername}/{datetime}/{content_type}.{extension}'
DBBACKUP_MEDIA_FILENAME_TEMPLATE = 'backups/{servername}/{datetime}/{content_type}.{extension}'

NEWRELIC_ENV = 'production'

AWS_SES_ACCESS_KEY_ID = 'AKIAJZ44WHPOEURR4TZA'
AWS_SES_SECRET_ACCESS_KEY = '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'

POST_OFFICE = {
    'LOG_LEVEL': 1,  # Log only failed emails
    'BACKENDS': {
        'ses': 'django_ses.SESBackend',
        'BATCH_SIZE': 10,
        'LOG_LEVEL': 1
    }
}

LDAP_CLIENT_URI = "ldap://review.compscicenter.ru:389"
LDAP_DB_SUFFIX = "dc=review,dc=compscicenter,dc=ru"
LDAP_CLIENT_USERNAME = "admin"
LDAP_CLIENT_PASSWORD = "C7G92?V6;c3M4.]e}k(Us33]"
LDAP_TLS_TRUSTED_CA_CERT_FILE = str(PROJECT_DIR / "LDAPTrustedCA.crt")
LDAP_SYNC_PASSWORD = True

GERRIT_API_URI = "https://review.compscicenter.ru/a/"
GERRIT_CLIENT_USERNAME = "admin"
GERRIT_CLIENT_HTTP_PASSWORD = "vV/rlPcuR3fTSv1ns3k3RT5xUV78qKhAMT/Xqf71Yg"

REDIS_PASSWORD = '3MUvZ/wV{6e86jq@x4uA%RDn9KbrV#WU]A=L76J@Q9iCa*9+vN'
THUMBNAIL_REDIS_PASSWORD = REDIS_PASSWORD
for queue in RQ_QUEUES.values():
    if 'PASSWORD' in queue:
        queue['PASSWORD'] = REDIS_PASSWORD


RECAPTCHA_PUBLIC_KEY = '6Ld2I7UUAAAAAMXFidlDOGnTTFQ3Zv3IhOcXbYoa'
RECAPTCHA_PRIVATE_KEY = '6Ld2I7UUAAAAAAD8zdSGOJ3bDMYJN0q23nzArzjd'
