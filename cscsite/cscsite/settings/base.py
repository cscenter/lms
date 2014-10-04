"""
Django settings for cscsite project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
from unipath import Path
import os

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

PROJECT_DIR = Path(__file__).ancestor(3)
MEDIA_ROOT = PROJECT_DIR.child("media")
MEDIA_URL = "/media/"
STATIC_ROOT = PROJECT_DIR.child("static")

STATICFILES_DIRS = (
    PROJECT_DIR.child("assets"),
)

TEMPLATE_DIRS = (
    PROJECT_DIR.child("templates"),
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader'
)


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '***REMOVED***'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []

SITE_ID = 1

EMAIL_HOST = 'smtp.yandex.ru'
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER = 'noreply@compscicenter.ru'
# use dummy password to avoid accidental messing of real data
EMAIL_HOST_PASSWORD = 'dummy_password'
EMAIL_PORT = 465
# XXX remove after Django 1.7 is out.
EMAIL_BACKEND = 'crutches.compat.SSLEmailBackend'

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'sorl.thumbnail',
    'crispy_forms',
    'floppyforms',
    'bootstrap3',
    'taggit',
    'south',
    'rosetta',
    'sitemetrics',

    'users',
    'core',
    'news',
    'index',
    'textpages',
    'learning',
    'library',
    'crutches',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    'core.notifications.UnreadNotificationsCacheMiddleware'
)

ROOT_URLCONF = 'cscsite.urls'

WSGI_APPLICATION = 'cscsite.wsgi.application'

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request',

    'core.context_processors.redirect_bases'
)

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'cscdb',
        'USER': 'csc',
        'PASSWORD': 'FooBar',
        'HOST': 'localhost',
        'PORT': ''
        }
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'ru'
LANGUAGES = (
    ('ru', "Russian"),)
LOCALE_PATHS = (
    "conf/locale",
)

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'

AUTH_USER_MODEL = "users.CSCUser"
AUTHENTICATION_BACKENDS = (
    "crutches.compat.EmailOrUsernameModelBackend",
)

# URL names info for top menu. Possible keys:
# "parent": name of "parent" menu item, as if in submenu
# "alias": name of "alias" to current url name, when highlighted menu entry
#          should differ from current url
# cscsite.core.templatetags.navigation will comply if there is no entry for
# current URL name

MENU_URL_NAMES = {
    'index': {},
    'about': {},
    'online': {},
    'teaching': {},
    'learning': {},
    'enrollment': {},

    'syllabus': {'parent': 'about'},
    'course_list': {'parent': 'about'},
    'course_detail': {'alias': 'course_list'},
    'class_detail': {'alias': 'course_list'},
    'course_offering_detail': {'alias': 'course_list'},
    'course_class_add': {'alias': 'course_list'},
    'course_class_edit': {'alias': 'course_list'},
    'course_class_delete': {'alias': 'course_list'},
    'course_offering_news_create': {'alias': 'course_list'},
    'course_offering_news_update': {'alias': 'course_list'},
    'course_offering_news_delete': {'alias': 'course_list'},
    'course_offering_edit_descr': {'alias': 'course_list'},
    'course_offering_unenroll': {},
    'orgs': {'parent': 'about'},
    'teachers': {'parent': 'about'},
    'teacher_detail': {'alias': 'teachers'},
    'alumni': {'parent': 'about'},

    'news_list': {},
    'news_detail': {'alias': 'news_list'},

    'assignment_list_student': {'parent': 'learning'},
    'timetable_student': {'parent': 'learning'},
    'calendar_student': {'alias': 'timetable_student'},
    'calendar_full_student': {'parent': 'learning'},
    'course_list_student': {'parent': 'learning'},
    'library_book_list': {'parent': 'learning'},
    'library_book_detail': {'parent': 'library_book_list'},
    'useful_stuff': {'parent': 'learning'},

    'assignment_list_teacher': {'parent': 'teaching'},
    'assignment_detail_teacher': {'alias': 'assignment_list_teacher'},
    'assignment_add': {'alias': 'assignment_list_teacher'},
    'assignment_edit': {'alias': 'assignment_list_teacher'},
    'assignment_delete': {'alias': 'assignment_list_teacher'},
    'timetable_teacher': {'parent': 'teaching'},
    'calendar_teacher': {'alias': 'timetable_teacher'},
    'calendar_full_teacher': {'parent': 'teaching'},
    'course_list_teacher': {'parent': 'teaching'},
    'course_edit': {'alias': 'courses_teacher'},
    'markssheet_teacher': {'parent': 'teaching'},

    'markssheet_staff': {},
    'user_detail': {},
    'custom_text_page': {},

    'a_s_detail_teacher': {'alias': 'assignment_list_teacher'},
    'a_s_detail_student': {'alias': 'assignment_list_student'},

    'contacts': {},
    'venue_detail': {},

    'user_update': {},
    'login': {},
    'logout': {},

    'password_change_complete': {},
    'password_reset_complete': {},
    'password_reset_confirm': {},
    'password_reset_done': {},
    'password_reset': {},
    'password_change': {}
    }

LOGIN_URL= "/login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
# this urls will be used to redirect from '/learning/' and '/teaching/'
LEARNING_BASE = 'assignment_list_student'
TEACHING_BASE = 'assignment_list_teacher'

CRISPY_TEMPLATE_PACK = 'bootstrap3'

# don't know what will happen if we change this when there are models in DB
SPRING_TERM_START = '10 jan'
AUTUMN_TERM_START = '10 aug'

THUMBNAIL_DEBUG = False

# use dummy values to avoid accidental messing of real data
SLIDESHARE_API_KEY = "dummy_ss_key"
SLIDESHARE_SECRET = "dummy_ss_secret"
SLIDESHARE_USERNAME = "dummy_ss_username"
SLIDESHARE_PASSWORD = "dummy_ss_password"

YANDEX_DISK_USERNAME = "dummy_ya_username"
YANDEX_DISK_PASSWORD = "dummy_ya_password"
YANDEX_DISK_SLIDES_ROOT = "dummy_ya_root"

SOUTH_MIGRATION_MODULES = {
    'taggit': 'taggit.south_migrations',
}
