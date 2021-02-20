# Read project environment into os.environ before importing base configuration
import environ
import sys
import warnings

env = environ.Env()
# Try to read .env file, if it's not present, assume that application
# is deployed to production and skip reading the file
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    environ.Env.read_env(env_file=env.str('ENV_FILE', default=None))

from lms.settings.extended import *

sys.path.append(str(Path(__file__).parents[1] / "apps"))

SITE_ID = 3
if REDIS_DB_INDEX is None:
    for queue_config in RQ_QUEUES.values():
        queue_config['DB'] = SITE_ID
    THUMBNAIL_REDIS_DB = SITE_ID

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["lk.yandexdataschool.ru"])

WSGI_APPLICATION = 'lk_yandexdataschool_ru.wsgi.application'
ROOT_URLCONF = 'lk_yandexdataschool_ru.urls'
LMS_SUBDOMAIN = None
LMS_CURATOR_EMAIL = 'shadcurators@yandex.ru'
LMS_MENU = 'lk_yandexdataschool_ru.menu'
SUBDOMAIN_URLCONFS = {
    None: ROOT_URLCONF,
}

INSTALLED_APPS += [
    'application.apps.ApplicationConfig',
]

ESTABLISHED = 2007
DEFAULT_CITY_CODE = "msk"
DEFAULT_BRANCH_CODE = "msk"

# Template customization
FAVICON_PATH = 'v1/img/shad/favicon.ico'
LOGO_PATH = 'v1/img/shad/logo.svg'

for template in TEMPLATES:
    if "Jinja2" in template["BACKEND"]:
        update_constants = [
            ("ESTABLISHED", ESTABLISHED),
            ("FAVICON_PATH", FAVICON_PATH),
            ("LOGO_PATH", LOGO_PATH)
        ]
        for option, value in update_constants:
            template["OPTIONS"]["constants"][option] = value


# Application form webhook authorization token. Send it over https only.
APPLICATION_FORM_SECRET_TOKEN = 'eb224e98-fffa-4e21-ab92-744f2e95e551-3f2a5499-89bf-4f8b-9c90-117b960f0fdf'
