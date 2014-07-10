from .base import *

INSTALLED_APPS += ('fixture_media', 'debug_toolbar', 'rosetta')

ROSETTA_MESSAGES_SOURCE_LANGUAGE_CODE = 'ru'
ROSETTA_MESSAGES_SOURCE_LANGUAGE_NAME = 'Russian'

THUMBNAIL_DEBUG = True

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = False
EMAIL_HOST = 'localhost'
EMAIL_PORT = 1025
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
DEFAULT_FROM_EMAIL = 'test@foo.bar'