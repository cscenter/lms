# Read project environment into os.environ before importing base configuration
import environ
env = environ.Env()
environ.Env.read_env(env_file=env.str('ENV_FILE', default=None))

from lms.settings.extended import *

SITE_ID = 3
if REDIS_DB_INDEX is None:
    for queue_config in RQ_QUEUES.values():
        queue_config['DB'] = SITE_ID
    THUMBNAIL_REDIS_DB = SITE_ID

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["lk.yandexdataschool.ru"])

WSGI_APPLICATION = 'lk_yandexdataschool_ru.wsgi.application'
ROOT_URLCONF = 'lms.urls'
# FIXME: move to the SiteConfiguration model
LMS_SUBDOMAIN = None

SUBDOMAIN_URLCONFS = {
    None: ROOT_URLCONF,
}

DEFAULT_CITY_CODE = "msk"
DEFAULT_BRANCH_CODE = "msk"

# Template customization
ESTABLISHED = 2007
FAVICON_PATH = 'v1/img/shad/favicon.ico'
LOGO_PATH = 'v1/img/shad/logo.svg'

for template in TEMPLATES:
    if "Jinja2" in template["BACKEND"]:
        update_options = [("ESTABLISHED", ESTABLISHED), ("FAVICON_PATH", FAVICON_PATH), ("LOGO_PATH", LOGO_PATH)]
        for option, value in update_options:
            template["OPTIONS"]["constants"][option] = value
