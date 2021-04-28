# Read project environment into os.environ before importing base configuration
import sys
import warnings

import environ

env = environ.Env()
# Try to read .env file, if it's not present, assume that application
# is deployed to production and skip reading the file
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    environ.Env.read_env(env_file=env.str('ENV_FILE', default=None))

from lms.settings.base import *

sys.path.append(str(ROOT_DIR / "compsciclub_ru" / "apps"))

SITE_ID = 2
if REDIS_DB_INDEX is None:
    for queue_config in RQ_QUEUES.values():
        queue_config['DB'] = SITE_ID
    THUMBNAIL_REDIS_DB = SITE_ID

PROJECT_DIR = Path(__file__).parents[1]

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[".compsciclub.ru"])

WSGI_APPLICATION = 'compsciclub_ru.wsgi.application'
ROOT_URLCONF = 'compsciclub_ru.urls'
LMS_CURATOR_EMAIL = None
if YANDEX_METRIKA_ID is None:
    YANDEX_METRIKA_ID = 32180204
SUBDOMAIN_URLCONFS = {
    None: ROOT_URLCONF
}

# FIXME: lms.base там другие миддлвары.
MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.sites.middleware.CurrentSiteMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'notifications.middleware.UnreadNotificationsCacheMiddleware',
    'core.middleware.SubdomainBranchMiddleware',
    'core.middleware.RedirectMiddleware',
]

INSTALLED_APPS += [
    'international_schools.apps.Config',
    'info_blocks.apps.InfoBlocksConfig',
    'grading.apps.ContestsConfig',
    'compsciclub_ru.project_conf.ProjectConfig',  # should be the last one
]
LOCALE_PATHS = [
    str(PROJECT_DIR / "locale"),
] + LOCALE_PATHS


ESTABLISHED = 2007

FAVICON_PATH = 'v1/img/club/favicon.ico'
LOGO_PATH = 'v1/img/club/logo.svg'

# Append project template dirs
for template in TEMPLATES:
    if "Jinja2" in template["BACKEND"]:
        template["DIRS"] = [str(PROJECT_DIR / "jinja2")] + template["DIRS"]
        template["OPTIONS"]["constants"]["YANDEX_METRIKA_ID"] = YANDEX_METRIKA_ID
        template["OPTIONS"]["globals"]["get_branches"] = "compsciclub_ru.context_processors.get_branches"
        update_constants = [
            ("ESTABLISHED", ESTABLISHED),
            ("FAVICON_PATH", FAVICON_PATH),
            ("LOGO_PATH", LOGO_PATH)
        ]
        for option, value in update_constants:
            template["OPTIONS"]["constants"][option] = value
    elif "DjangoTemplates" in template["BACKEND"]:
        template["DIRS"] = [str(PROJECT_DIR / "templates")] + template["DIRS"]
        template["OPTIONS"]["context_processors"] += ("compsciclub_ru.context_processors.get_branches",)

# FIXME: hz
FORM_RENDERER = 'django.forms.renderers.DjangoTemplates'

# Public registration settings
ACCOUNT_ACTIVATION_DAYS = 2
INCLUDE_REGISTER_URL = False
INCLUDE_AUTH_URLS = False
REGISTRATION_FORM = 'compsciclub_ru.forms.RegistrationUniqueEmailAndUsernameForm'

# Disable migrations
MIGRATION_MODULES = {
    "core": None,
    "courses": None,
    "htmlpages": None,
    "learning": None,
    "tasks": None,
    "gallery": None,
    "notifications": None,
    "library": None,
    "study_programs": None,
    "users": None,
    "grading": None,
}
