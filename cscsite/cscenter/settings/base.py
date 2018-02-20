"""
CS center app specific settings
"""

from core.settings.base import *

SITE_ID = 1
ROOT_URLCONF = 'cscenter.urls'
WSGI_APPLICATION = 'cscenter.wsgi.application'

BASE_DIR = Path(__file__).parents[1]

MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    'core.middleware.CurrentCityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'users.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'core.notifications.UnreadNotificationsCacheMiddleware',
    'learning.middleware.StudentCityMiddleware',
    'core.middleware.RedirectMiddleware',
]
INSTALLED_APPS += [
    'learning.admission.apps.AdmissionConfig',
    # 'django_ses'
    'post_office',
    'admission_test',  # TODO: remove after testing
]

SOCIAL_AUTH_YANDEXRU_KEY = "4ac0b41c382a4dba9d8aeaa9a29d663b"
SOCIAL_AUTH_YANDEXRU_SECRET = "8d708acac5d8422e8c4973d5bf2fa568"
SOCIAL_AUTH_YANDEXRU_PIPELINE = [
    'social_core.pipeline.social_auth.social_details',
    # 'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
]

# Add site specific templates
TEMPLATES[0]['DIRS'] = [
    str(BASE_DIR / "templates"),
    str(PROJECT_DIR / "admission_test" / "templates"),
] + TEMPLATES[0]['DIRS']

LOCALE_PATHS += [
    str(BASE_DIR / "locale"),
    str(PROJECT_DIR / "learning" / "projects" / "locale"),
    str(PROJECT_DIR / "learning" / "admission" / "locale"),
]
# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'chf0ao=8=ihflu_ln2&z+jke)*cx=k0e3mzuq+pc+x+6@vxrj7'

ALLOWED_HOSTS = []

DEFAULT_FROM_EMAIL = EMAIL_HOST_USER = 'noreply@compscicenter.ru'

GFORM_CALLBACK_SECRET = "X64WDCbOSgwJSgSsHroTHVX/TWo5wzddRkH+eRjCvrA="

NEWRELIC_CONF = str(BASE_DIR / "newrelic.ini")
NEWRELIC_ENV = 'development'


AWS_SES_ACCESS_KEY_ID = ''
AWS_SES_SECRET_ACCESS_KEY = ''
AWS_SES_REGION_NAME = 'eu-west-1'
AWS_SES_REGION_ENDPOINT = 'email.eu-west-1.amazonaws.com'
POST_OFFICE = {
    'BACKENDS': {
        'ses': 'django.core.mail.backends.console.EmailBackend',
        'BATCH_SIZE': 10,
        'LOG_LEVEL': 1
    }
}

