from .base import *

DEBUG = False
for template in TEMPLATES:
    template['OPTIONS']['debug'] = DEBUG
ALLOWED_HOSTS = ["dev.compscicenter.ru"]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'test_cscdb',
        'USER': 'csc',
        'PASSWORD': 'FooBar',
        'HOST': 'localhost',
        'PORT': ''
    }
}


CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': '/tmp/django_cache'
    }
}

THUMBNAIL_DEBUG = False

EMAIL_HOST = '127.0.0.1'
EMAIL_HOST_PASSWORD = ''
EMAIL_PORT = 1025
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True


LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        'sentry': {
            'level': 'WARNING',
            'class': 'raven.contrib.django.raven_compat.handlers.SentryHandler',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        }
    },
    'loggers': {
        '': {
            'level': 'WARNING',
            'handlers': ['sentry'],
        },
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
        'raven': {
            'level': 'WARNING',
            'handlers': ['console'],
            'propagate': False,
        },
        'sentry.errors': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False,
        },
    },
}


FILE_UPLOAD_HANDLERS = [
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
]

FILE_UPLOAD_MAX_MEMORY_SIZE = 26214400

THUMBNAIL_KVSTORE = 'sorl.thumbnail.kvstores.cached_db_kvstore.KVStore'
