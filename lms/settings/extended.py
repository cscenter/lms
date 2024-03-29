"""
Settings that are not used by club site
"""

from .base import *

INSTALLED_APPS += [
    'lms',
    'post_office',
    'django_jinja',
    'library.apps.LibraryConfig',
    'projects.apps.ProjectsConfig',
    'stats.apps.StatisticsConfig',
    'admission.apps.AdmissionConfig',
    'staff',
    'surveys.apps.SurveysConfig',
    'info_blocks.apps.InfoBlocksConfig',
    'code_reviews.apps.CodeReviewsConfig',
    'grading.apps.ContestsConfig',
    'faq.apps.FAQConfig',
    'ckeditor',
    'ckeditor_uploader',
]

for template in TEMPLATES:
    if "Jinja2" in template["BACKEND"]:
        template["DIRS"] += [
            str(SHARED_APPS_DIR / "surveys" / "jinja2"),
            # svg inline support
            str(WEBPACK_ASSETS_ROOT / "v2" / "dist" / "img"),
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

SOCIAL_AUTH_JSONFIELD_ENABLED = True
# Admission app authentication
# Oauth settings for getting access to login from Yandex.Passport
# Note: Application is managed by `contest@compscicenter.ru` yandex account
SOCIAL_AUTH_YANDEXRU_KEY = env.str('SOCIAL_AUTH_YANDEXRU_KEY')
SOCIAL_AUTH_YANDEXRU_SECRET = env.str('SOCIAL_AUTH_YANDEXRU_SECRET')
# Prevent calling pipeline for this backend
SOCIAL_AUTH_YANDEXRU_PIPELINE: List[str] = []

# Code review integration
LDAP_CLIENT_URI = env.str('LDAP_CLIENT_URI', default="ldap://review.compscicenter.ru:389")
# Domain Component suffix for distinguished name (or DN)
LDAP_DB_SUFFIX = env.str('LDAP_DB_SUFFIX', default="dc=review,dc=compscicenter,dc=ru")
LDAP_CLIENT_USERNAME = env.str('LDAP_CLIENT_USERNAME', default="admin")
LDAP_CLIENT_PASSWORD = env.str('LDAP_CLIENT_PASSWORD')
LDAP_SYNC_PASSWORD = env.bool('LDAP_SYNC_PASSWORD', default=True)
LDAP_OVER_SSL_ENABLED = env.bool('LDAP_OVER_SSL_ENABLED', default=True)
GERRIT_API_URI = env.str('GERRIT_API_URI', default="https://review.compscicenter.ru/a/")
GERRIT_CLIENT_USERNAME = env.str('GERRIT_CLIENT_USERNAME', default="admin")
GERRIT_CLIENT_HTTP_PASSWORD = env.str('GERRIT_CLIENT_HTTP_PASSWORD')
GERRIT_ROBOT_USERNAME = env.str('GERRIT_ROBOT_USERNAME', default="gerrit.bot")
GERRIT_TEST_STUDENT_PASSWORD = env.str('GERRIT_TEST_STUDENT_PASSWORD', default="")
LDAP_TLS_TRUSTED_CA_CERT_FILE = env.str('LDAP_TLS_TRUSTED_CA_CERT_FILE', default=str(ROOT_DIR / "lms" / "LDAPTrustedCA.crt"))

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

