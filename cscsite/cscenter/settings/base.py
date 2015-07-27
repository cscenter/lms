"""
CS center app specific settings
"""

from unipath import Path
from core.settings.base import *

SITE_ID = 1
ROOT_URLCONF = 'cscenter.urls'
WSGI_APPLICATION = 'cscenter.wsgi.application'

BASE_DIR = Path(__file__).ancestor(2)

LOCALE_PATHS = (
    Path(BASE_DIR, "locale"),
)
# Add site specific templates
TEMPLATES[0]['DIRS'] += [BASE_DIR.child("templates")]

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'chf0ao=8=ihflu_ln2&z+jke)*cx=k0e3mzuq+pc+x+6@vxrj7'

ALLOWED_HOSTS = []

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER = 'noreply@compscicenter.ru'

GFORM_CALLBACK_SECRET = "X64WDCbOSgwJSgSsHroTHVX/TWo5wzddRkH+eRjCvrA="

NEWRELIC_CONF = Path(BASE_DIR, "newrelic.ini")
NEWRELIC_ENV = 'development'
