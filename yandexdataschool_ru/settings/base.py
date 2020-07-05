# Read project environment into os.environ before importing base configuration
import environ
env = environ.Env()
environ.Env.read_env(env_file=env.str('ENV_FILE', default=None))

from lms.settings.base import *

SITE_ID = 3

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["lk.yandexdataschool.ru"])

WSGI_APPLICATION = 'yandexdataschool_ru.wsgi.application'
ROOT_URLCONF = 'lms.urls'
# FIXME: move to the SiteConfiguration model
LMS_SUBDOMAIN = None

SUBDOMAIN_URLCONFS = {
    None: ROOT_URLCONF,
}
