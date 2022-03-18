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

FILE_UPLOAD_HANDLERS = [
    "django.core.files.uploadhandler.TemporaryFileUploadHandler",
]

REST_FRAMEWORK['DEFAULT_RENDERER_CLASSES'] = (
    'rest_framework.renderers.JSONRenderer',
    'rest_framework.renderers.BrowsableAPIRenderer',
)

SILENCED_SYSTEM_CHECKS = ['captcha.recaptcha_test_key_error']
