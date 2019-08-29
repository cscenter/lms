from .base import *

# Test settings

TEST_RUNNER = 'django.test.runner.DiscoverRunner'
TEST_DISCOVER_TOP_LEVEL = str(APPS_DIR)
TEST_DISCOVER_ROOT = str(APPS_DIR)
TEST_DISCOVER_PATTERN = "test_*"

# django-coverage settings

COVERAGE_REPORT_HTML_OUTPUT_DIR = str(APPS_DIR / "coverage")
COVERAGE_USE_STDOUT = True
COVERAGE_MODULE_EXCLUDES = ['tests$', 'settings$', 'urls$', 'locale$',
                            'common.views.test', '__init__', 'django',
                            'migrations', '^sorl', '__pycache__']
COVERAGE_PATH_EXCLUDES = [r'.svn', r'fixtures', r'node_modules']

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
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

# FIXME: remove
REDIS_PASSWORD = None
THUMBNAIL_REDIS_PASSWORD = REDIS_PASSWORD
for queue in RQ_QUEUES.values():
    if 'PASSWORD' in queue:
        queue['PASSWORD'] = REDIS_PASSWORD

