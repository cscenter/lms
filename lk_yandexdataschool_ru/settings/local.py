import socket

from .base import *

# XXX: js-reverse depends on ROOT_URLCONF and doesn't play well
# with SUBDOMAIN_URLCONFS
INSTALLED_APPS += ['django_js_reverse']
JS_REVERSE_JS_VAR_NAME = 'URLS'
JS_REVERSE_INCLUDE_ONLY_NAMESPACES = ['stats-api', 'admission-api']
JS_REVERSE_OUTPUT_PATH = str(DJANGO_ASSETS_ROOT / "v1" / "js" / "vendor")


hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
INTERNAL_IPS = [ip[:-1] + '1' for ip in ips] + ["127.0.0.1", "::1"]

if DEBUG:
    INSTALLED_APPS += ['django_extensions']
    try:
        # Enable Django debug toolbar
        import debug_toolbar

        MIDDLEWARE = ['debug_toolbar.middleware.DebugToolbarMiddleware'] + MIDDLEWARE
        INSTALLED_APPS = INSTALLED_APPS + ['debug_toolbar']
    except ModuleNotFoundError as err:
        warnings.warn(str(err), ImportWarning)

    # Translate .po files with UI
    INSTALLED_APPS = INSTALLED_APPS + ['rosetta']
    ROSETTA_MESSAGES_SOURCE_LANGUAGE_CODE = 'ru'
    ROSETTA_MESSAGES_SOURCE_LANGUAGE_NAME = 'Russian'


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
            '()': 'core.logging.SQLFormatter',
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

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
)

SILENCED_SYSTEM_CHECKS = ['captcha.recaptcha_test_key_error']
