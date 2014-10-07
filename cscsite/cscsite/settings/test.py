from .base import *

# Test settings

#TEST_RUNNER = "discover_runner.DiscoverRunner"
#TEST_RUNNER = 'django_coverage.coverage_runner.CoverageRunner'
TEST_RUNNER = 'core.test_runners.ColoredCoverageRunner'
TEST_DISCOVER_TOP_LEVEL = PROJECT_DIR
TEST_DISCOVER_ROOT = PROJECT_DIR
TEST_DISCOVER_PATTERN = "test_*"

# django-coverage settings

COVERAGE_REPORT_HTML_OUTPUT_DIR = PROJECT_DIR.child("coverage")
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

SOUTH_TESTS_MIGRATE = False

# This makes tests almost 2x faster; we don't need strong security and DEBUG
# during tests
PASSWORD_HASHERS = (
    'django.contrib.auth.hashers.MD5PasswordHasher',
)
DEBUG = False
TEMPLATE_DEBUG = False
