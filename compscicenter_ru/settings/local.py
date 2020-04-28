from .base import *

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware'
] + MIDDLEWARE
INTERNAL_IPS = ["127.0.0.1", "::1"]

INSTALLED_APPS += [
    'debug_toolbar',
    'django_extensions',
    'django_js_reverse',
    # 'template_timings_panel',
    'rosetta'
]

ROSETTA_MESSAGES_SOURCE_LANGUAGE_CODE = 'ru'
ROSETTA_MESSAGES_SOURCE_LANGUAGE_NAME = 'Russian'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
        'sql': {
            '()': 'core.utils.SQLFormatter',
            'format': '[%(duration).3f] %(statement)s',
        },
        'rq_console': {
            'format': '%(asctime)s %(message)s',
            'datefmt': '%H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'rq_console': {
            'level': 'DEBUG',
            'class': 'rq.utils.ColorizingStreamHandler',
            'formatter': 'rq_console',
            'exclude': ['%(asctime)s'],
        },
        'sql': {
            'class': 'logging.StreamHandler',
            'formatter': 'sql',
            'level': 'DEBUG',
        },
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        # root logger
        '': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'django': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'django.db.backends': {
            'handlers': ['null'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.utils.autoreload': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.db.backends.schema': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django.server': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.template': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'notifications.handlers': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        "notifications.notifier": {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        "rq.worker": {
            "handlers": ["rq_console"],
            "level": "DEBUG",
            'propagate': False,
        },
        "post_office": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}


FILE_UPLOAD_HANDLERS = [
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
]

FILE_UPLOAD_MAX_MEMORY_SIZE = 26214400


# Disable django-debug-toolbar jquery
DEBUG_TOOLBAR_CONFIG = {
    # 'SHOW_TOOLBAR_CALLBACK': lambda r: False,  # disables it
}

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
)

SILENCED_SYSTEM_CHECKS = ['captcha.recaptcha_test_key_error']


# django-js-reverse app settings
JS_REVERSE_JS_VAR_NAME = 'URLS'
JS_REVERSE_INCLUDE_ONLY_NAMESPACES = ['stats-api', 'admission-api']
JS_REVERSE_OUTPUT_PATH = str(ASSETS_ROOT / "v1" / "js" / "vendor")


WEBPACK_LOADER = {
    'V1': {
        'BUNDLE_DIR_NAME': 'v1/dist/.local/',  # relative to the ASSETS_ROOT
        'STATS_FILE': str(ASSETS_ROOT / "v1" / "dist" / ".local" / "webpack-stats-v1.json"),
    },
    'V2': {
        'BUNDLE_DIR_NAME': 'v2/dist/.local/',  # relative to the ASSETS_ROOT
        'STATS_FILE': str(ASSETS_ROOT / "v2" / "dist" / ".local" / "webpack-stats-v2.json"),
    }
}
