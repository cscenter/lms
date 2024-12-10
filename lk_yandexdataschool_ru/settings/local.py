import socket

from .base import *

# XXX: js-reverse depends on ROOT_URLCONF and doesn't play well
# with SUBDOMAIN_URLCONFS
INSTALLED_APPS += ['django_js_reverse']
JS_REVERSE_JS_VAR_NAME = 'URLS'
JS_REVERSE_INCLUDE_ONLY_NAMESPACES = ['stats-api', 'admission-api']
JS_REVERSE_OUTPUT_PATH = str(DJANGO_ASSETS_ROOT / "v1" / "js" / "vendor")

if DEBUG:
    INSTALLED_APPS += ['django_extensions']
    # Django swagger api overview
    INSTALLED_APPS += ['drf_yasg']
    # Translate .po files with UI
    INSTALLED_APPS = INSTALLED_APPS + ['rosetta']
    ROSETTA_MESSAGES_SOURCE_LANGUAGE_CODE = 'ru'
    ROSETTA_MESSAGES_SOURCE_LANGUAGE_NAME = 'Russian'

FILE_UPLOAD_HANDLERS = [
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
]

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
)

SILENCED_SYSTEM_CHECKS = ['captcha.recaptcha_test_key_error']
