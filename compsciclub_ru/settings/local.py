from .base import *

INTERNAL_IPS = ["127.0.0.1", "::1"]

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

FILE_UPLOAD_HANDLERS = ("django.core.files.uploadhandler.TemporaryFileUploadHandler",)

SILENCED_SYSTEM_CHECKS = ['captcha.recaptcha_test_key_error']
