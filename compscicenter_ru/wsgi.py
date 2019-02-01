"""
WSGI config for the project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/howto/deployment/wsgi/
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "compscicenter_ru.settings.production")

import newrelic.agent
from django.conf import settings
newrelic.agent.initialize(settings.NEWRELIC_CONF, settings.NEWRELIC_ENV)

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
