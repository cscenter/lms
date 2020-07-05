"""
WSGI config for the project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                      "yandexdataschool_ru.settings.production")

from django.conf import settings

if hasattr(settings, "NEWRELIC_ENV"):
    import newrelic.agent
    newrelic.agent.initialize(settings.NEWRELIC_CONF, settings.NEWRELIC_ENV)

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
