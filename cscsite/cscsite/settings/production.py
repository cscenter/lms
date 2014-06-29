# -*- coding: utf-8 -*-

from __future__ import absolute_import

from .base import *

TEMPLATE_DEBUG = DEBUG = False

ALLOWED_HOSTS = ["gamma.compscicenter.ru"]

# Logging-related stuff
RAVEN_CONFIG = {
    # Note(lebedev): see https://app.getsentry.com/cscenter/cscenter/docs/django
    # for instructions.
    "dsn": "https://7d2d63dd1ba84e149d2cf42e21179dfb:825f3d7218284ab3a7334ff5d2077e02@app.getsentry.com/13763"
}

INSTALLED_APPS += ('raven.contrib.django.raven_compat', )

LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'root': {
        'level': 'WARNING',
        'handlers': ['sentry'],
    },
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
        'raven': {
            'level': 'DEBUG',
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
