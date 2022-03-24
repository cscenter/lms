from .base import *

if DEBUG:
    INSTALLED_APPS += ['django_extensions']
    # Translate .po files with UI
    INSTALLED_APPS = INSTALLED_APPS + ['rosetta']
    ROSETTA_MESSAGES_SOURCE_LANGUAGE_CODE = 'ru'
    ROSETTA_MESSAGES_SOURCE_LANGUAGE_NAME = 'Russian'

FILE_UPLOAD_HANDLERS = ("django.core.files.uploadhandler.TemporaryFileUploadHandler",)

SILENCED_SYSTEM_CHECKS = ['captcha.recaptcha_test_key_error']
