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


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '***REMOVED***'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    'sorl.thumbnail',
    'crispy_forms',
    'floppyforms',
    'taggit',

    'users',
    'core',
    'news',
    'index',
    'textpages',
    'learning',
    'library',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
    # 'default': {
    #     'ENGINE': 'django.db.backends.sqlite3',
    #     'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    # }
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
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

# Custom user model

AUTH_USER_MODEL = "users.CSCUser"

# URL names info for top menu. Possible keys:
# "parent": name of "parent" menu item, as if in submenu
# "alias": name of "alias" to current url name, when highlighted menu entry
#          should differ from current url
# cscsite.core.templatetags.navigation will comply if there is no entry for
# current URL name

MENU_URL_NAMES = {
    'index': {},

    'syllabus': {'parent': 'about'},
    'course_list': {'parent': 'about'},
    # TODO: link-walking!
    'course_offering_detail': {'alias': 'course_list'},
    'orgs': {'parent': 'about'},
    'profs': {'parent': 'about'},
    'alumni': {'parent': 'about'},

    'news_list': {},
    'news_detail': {'alias': 'news_list'},

    'assignment_list_student': {'parent': 'learning'},
    'timetable_student': {'parent': 'learning'},
    'calendar_student': {'alias': 'timetable_student'},
    'calendar_full_student': {'parent': 'learning'},
    'course_list_student': {'parent': 'learning'},

    'assignment_list_teacher': {'parent': 'teaching'},
    'timetable_teacher': {'parent': 'teaching'},
    'calendar_teacher': {'alias': 'timetable_teacher'},
    'calendar_full_teacher': {'parent': 'teaching'},
    'course_list_teacher': {'parent': 'teaching'},
    # TODO: allow link-walking on "alias" for 'alias': 'courses_teacher'
    'course_edit': {'alias': 'courses_teacher'},
    'markssheet_teacher': {'parent': 'teaching'},

    'contacts': {},

    'login': {},
    'logout': {}
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
