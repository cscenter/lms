# Read project environment into os.environ before importing base configuration
import environ
import sys

env = environ.Env()
environ.Env.read_env(env_file=env.str('ENV_FILE', default=None))

from lms.settings.extended import *

sys.path.append(str(ROOT_DIR / "compscicenter_ru" / "apps"))

SITE_ID = 1
if REDIS_DB_INDEX is None:
    for queue_config in RQ_QUEUES.values():
        queue_config['DB'] = SITE_ID
    THUMBNAIL_REDIS_DB = SITE_ID

PROJECT_DIR = Path(__file__).parents[1]

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[".compscicenter.ru"])

WSGI_APPLICATION = 'compscicenter_ru.wsgi.application'
ROOT_URLCONF = 'compscicenter_ru.urls'
# FIXME: move to the SiteConfiguration model
LMS_SUBDOMAIN = 'my'
if YANDEX_METRIKA_ID is None:
    YANDEX_METRIKA_ID = 25844420

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

# Append project template dirs
for template in TEMPLATES:
    if "Jinja2" in template["BACKEND"]:
        template["DIRS"] = [str(PROJECT_DIR / "jinja2")] + template["DIRS"]
        template["OPTIONS"]["constants"]["YANDEX_METRIKA_ID"] = YANDEX_METRIKA_ID
    elif "DjangoTemplates" in template["BACKEND"]:
        template["DIRS"] = [str(PROJECT_DIR / "templates")] + template["DIRS"]

CACHES['social_networks'] = {
    'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
    'LOCATION': str(ROOT_DIR / ".cache")
}


# Append project translation
LOCALE_PATHS = [str(PROJECT_DIR / "locale")] + LOCALE_PATHS

