"""
Settings that are not used by club site
"""

from .base import *

INSTALLED_APPS += [
    'dbbackup',
    'lms',
    'menu',
    'post_office',
    'django_jinja',
    'projects.apps.ProjectsConfig',
    'stats.apps.StatisticsConfig',
    'admission.apps.AdmissionConfig',
    'staff',
    'surveys.apps.SurveysConfig',
    'info_blocks.apps.InfoBlocksConfig',
    'faq.apps.FAQConfig',
    'ckeditor',
    'ckeditor_uploader',
]

for template in TEMPLATES:
    if "Jinja2" in template["BACKEND"]:
        template["DIRS"] += [
            str(SHARED_APPS_DIR / "surveys" / "jinja2"),
            # svg inline support
            str(ASSETS_ROOT / "v2" / "dist" / "img"),
        ]
    elif "DjangoTemplates" in template["BACKEND"]:
        template["DIRS"] += [
            str(SHARED_APPS_DIR / "admission" / "templates"),
            str(SHARED_APPS_DIR / "staff" / "templates"),
        ]

LOCALE_PATHS += [
    str(SHARED_APPS_DIR / "projects" / "locale"),
    str(SHARED_APPS_DIR / "admission" / "locale"),
    str(SHARED_APPS_DIR / "surveys" / "locale"),
]

# Admission app authentication
# Oauth settings for getting access to login from Yandex.Passport
# Note: Application is managed by `contest@compscicenter.ru` yandex account
SOCIAL_AUTH_YANDEXRU_KEY = env.str('SOCIAL_AUTH_YANDEXRU_KEY')
SOCIAL_AUTH_YANDEXRU_SECRET = env.str('SOCIAL_AUTH_YANDEXRU_SECRET')
# Prevent calling pipeline for this backend
SOCIAL_AUTH_YANDEXRU_PIPELINE = []

# Code review integration
LDAP_CLIENT_URI = env.str('LDAP_CLIENT_URI', default="ldap://review.compscicenter.ru:389")
# Domain Component suffix for distinguished name (or DN)
LDAP_DB_SUFFIX = env.str('LDAP_DB_SUFFIX', default="dc=review,dc=compscicenter,dc=ru")
LDAP_CLIENT_USERNAME = env.str('LDAP_CLIENT_USERNAME', default="admin")
LDAP_CLIENT_PASSWORD = env.str('LDAP_CLIENT_PASSWORD')
LDAP_SYNC_PASSWORD = env.bool('LDAP_SYNC_PASSWORD', default=True)
GERRIT_API_URI = env.str('GERRIT_API_URI', default="https://review.compscicenter.ru/a/")
GERRIT_CLIENT_USERNAME = env.str('GERRIT_CLIENT_USERNAME', default="admin")
GERRIT_CLIENT_HTTP_PASSWORD = env.str('GERRIT_CLIENT_HTTP_PASSWORD')

# Registration by invitation link
INCLUDE_REGISTER_URL = False
INCLUDE_AUTH_URLS = False
ACCOUNT_ACTIVATION_DAYS = 1
ACTIVATION_EMAIL_SUBJECT = 'emails/activation_email_subject.txt'
ACTIVATION_EMAIL_BODY = 'emails/activation_email_body.txt'

# Project app settings
YANDEX_DISK_CLIENT_ID = env.str('YANDEX_DISK_CLIENT_ID')
YANDEX_DISK_CLIENT_SECRET = env.str('YANDEX_DISK_CLIENT_SECRET')
YANDEX_DISK_ACCESS_TOKEN = env.str('YANDEX_DISK_ACCESS_TOKEN')
YANDEX_DISK_REFRESH_TOKEN = env.str('YANDEX_DISK_REFRESH_TOKEN')

# Mailing Settings
AWS_SES_ACCESS_KEY_ID = env.str('AWS_SES_ACCESS_KEY_ID')
AWS_SES_SECRET_ACCESS_KEY = env.str('AWS_SES_SECRET_ACCESS_KEY')
AWS_SES_REGION_NAME = env.str('AWS_SES_REGION_NAME', default='eu-west-1')
AWS_SES_REGION_ENDPOINT = env.str('AWS_SES_REGION_ENDPOINT', default='email.eu-west-1.amazonaws.com')
POST_OFFICE = {
    'BACKENDS': {
        'ses': 'django.core.mail.backends.console.EmailBackend',
        'BATCH_SIZE': 10,
        'LOG_LEVEL': 1
    }
}