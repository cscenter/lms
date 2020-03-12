from .base import *

DEBUG = False
MODELTRANSLATION_DEBUG = False
THUMBNAIL_DEBUG = False
for template in TEMPLATES:
    template['OPTIONS']['debug'] = DEBUG
    if 'auto_reload' in template['OPTIONS']:
        template['OPTIONS']['auto_reload'] = DEBUG



TEST_RUNNER = 'django.test.runner.DiscoverRunner'
TEST_DISCOVER_TOP_LEVEL = str(SHARED_APPS_DIR)
TEST_DISCOVER_ROOT = str(SHARED_APPS_DIR)
TEST_DISCOVER_PATTERN = "test_*"

# django-coverage settings

COVERAGE_REPORT_HTML_OUTPUT_DIR = str(SHARED_APPS_DIR / "coverage")
COVERAGE_USE_STDOUT = True
COVERAGE_MODULE_EXCLUDES = ['tests$', 'settings$', 'urls$', 'locale$',
                            'common.views.test', '__init__', 'django',
                            'migrations', '^sorl', '__pycache__']
COVERAGE_PATH_EXCLUDES = [r'.svn', r'fixtures', r'node_modules']

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "travis_ci_test",
        "USER": "postgres",
        "PASSWORD": "",
        "HOST": "localhost",
        "PORT": ""
    }
}

TEST_DOMAIN = 'compscicenter.ru'
TEST_DOMAIN_ID = 1
ANOTHER_DOMAIN = 'compsciclub.ru'
ANOTHER_DOMAIN_ID = 2
SITE_ID = TEST_DOMAIN_ID
ALLOWED_HOSTS = [f".{TEST_DOMAIN}", f".{ANOTHER_DOMAIN}"]

# This makes tests almost 2x faster; we don't need strong security and DEBUG
# during tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

MEDIA_ROOT = '/tmp/django_test_media/'

MIGRATION_MODULES = {}

LANGUAGE_CODE = 'en'

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'

THUMBNAIL_KVSTORE = 'sorl.thumbnail.kvstores.cached_db_kvstore.KVStore'

SILENCED_SYSTEM_CHECKS = ['captcha.recaptcha_test_key_error']

for queue_config in RQ_QUEUES.values():
    queue_config['ASYNC'] = False
