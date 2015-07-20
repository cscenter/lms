from .test import *

# This is a special testing settings for Travis and Python3, because
# django-coverage doesn't support Python3

TEST_RUNNER = 'django.test.runner.DiscoverRunner'
