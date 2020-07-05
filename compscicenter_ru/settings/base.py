# Read project environment into os.environ before importing base configuration
import environ
import sys
env = environ.Env()
environ.Env.read_env(env_file=env.str('ENV_FILE', default=None))

from lms.settings.base import *

sys.path.append(str(ROOT_DIR / "compscicenter_ru" / "apps"))

SITE_ID = 1

PROJECT_DIR = Path(__file__).parents[1]

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[".compscicenter.ru"])

WSGI_APPLICATION = 'compscicenter_ru.wsgi.application'
ROOT_URLCONF = 'compscicenter_ru.urls'
# FIXME: move to the SiteConfiguration model
LMS_SUBDOMAIN = 'my'

SUBDOMAIN_URLCONFS = {
    None: ROOT_URLCONF,
    LMS_SUBDOMAIN: 'lms.urls',
}

INSTALLED_APPS += [
    'compscicenter_ru',
    'announcements.apps.AnnouncementsConfig',
    'application.apps.ApplicationConfig',
    'online_courses.apps.Config',
    'publications.apps.PublicationsConfig',
]

NEWRELIC_CONF = str(PROJECT_DIR / "newrelic.ini")
NEWRELIC_ENV = env.str('NEWRELIC_ENV', default='production')

# Append project template dirs
for template in TEMPLATES:
    if "Jinja2" in template["BACKEND"]:
        template["DIRS"] = [str(PROJECT_DIR / "jinja2")] + template["DIRS"]
    elif "DjangoTemplates" in template["BACKEND"]:
        template["DIRS"] = [str(PROJECT_DIR / "templates")] + template["DIRS"]


# Append project translation
LOCALE_PATHS = [str(PROJECT_DIR / "locale")] + LOCALE_PATHS

LDAP_TLS_TRUSTED_CA_CERT_FILE = env.str('LDAP_TLS_TRUSTED_CA_CERT_FILE', default=str(PROJECT_DIR / "LDAPTrustedCA.crt"))