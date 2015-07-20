from .test import *

# This is a special testing settings for Travis and Python3, because
# django-coverage doesn't support Python3

TEST_RUNNER = 'django.test.runner.DiscoverRunner'

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

MIGRATION_MODULES = {}
