# Read project environment into os.environ before importing base configuration
import sys
import environ

env = environ.Env()
environ.Env.read_env(env_file=env.str('ENV_FILE', default=None))

from lms.settings.base import *

sys.path.append(str(ROOT_DIR / "compsciclub_ru" / "apps"))

SITE_ID = 2

PROJECT_DIR = Path(__file__).parents[1]

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[".compsciclub.ru"])

WSGI_APPLICATION = 'compsciclub_ru.wsgi.application'
ROOT_URLCONF = 'compsciclub_ru.urls'

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
    'core.middleware.CurrentBranchMiddleware',
    'core.middleware.RedirectMiddleware',
]

INSTALLED_APPS += [
    'international_schools.apps.Config',
    'info_blocks.apps.InfoBlocksConfig',
    'compsciclub_ru.project_conf.ProjectConfig',  # should be the last one
]
LOCALE_PATHS = [
    str(PROJECT_DIR / "locale"),
] + LOCALE_PATHS

# Append project template dirs
for template in TEMPLATES:
    if "Jinja2" in template["BACKEND"]:
        template["DIRS"] = [str(PROJECT_DIR / "jinja2")] + template["DIRS"]
        template["OPTIONS"]["globals"]["get_branches"] = "compsciclub_ru.context_processors.get_branches"
    elif "DjangoTemplates" in template["BACKEND"]:
        template["DIRS"] = [str(PROJECT_DIR / "templates")] + template["DIRS"]

# FIXME: hz
FORM_RENDERER = 'django.forms.renderers.DjangoTemplates'

NEWRELIC_CONF = str(PROJECT_DIR / "newrelic.ini")
NEWRELIC_ENV = env.str('NEWRELIC_ENV', default='production')

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
}
