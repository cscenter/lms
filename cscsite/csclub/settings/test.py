from .base import *

# Test settings

TEST_RUNNER = "discover_runner.DiscoverRunner"
TEST_DISCOVER_TOP_LEVEL = str(PROJECT_DIR)
TEST_DISCOVER_ROOT = str(PROJECT_DIR)
TEST_DISCOVER_PATTERN = "test_*"

# django-coverage settings

COVERAGE_REPORT_HTML_OUTPUT_DIR = str(PROJECT_DIR / "coverage")
COVERAGE_USE_STDOUT = True
COVERAGE_MODULE_EXCLUDES = ['tests$', 'settings$', 'urls$', 'locale$',
                            'common.views.test', '__init__', 'django',
                            'migrations', '^sorl', '__pycache__']
COVERAGE_PATH_EXCLUDES = [r'.svn', r'fixtures']

# In-memory test database

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "USER": "",
        "PASSWORD": "",
        "HOST": "",
        "PORT": ""
        }
    }

# This makes tests almost 2x faster; we don't need strong security and DEBUG
# during tests
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)
DEBUG = False
ALLOWED_HOSTS = [".compscicenter.ru", ".compsciclub.ru"]
for template in TEMPLATES:
    template['OPTIONS']['debug'] = DEBUG
MODELTRANSLATION_DEBUG = False

MEDIA_ROOT = '/tmp/django_test_media/'


class DisableMigrations(object):
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return "notmigrations"

LANGUAGE_CODE = 'en'

# disable migration in tests; it's a hack until Django 1.8 with --keepdb
# MIGRATION_MODULES = DisableMigrations()
MIGRATION_MODULES = {}

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
