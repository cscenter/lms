SHELL := /bin/sh

PROJECTS := compscicenter_ru compsciclub_ru
PROJECT := compscicenter_ru
PORT := 8000
SETTINGS_ENV := local
DJANGO_SETTINGS_MODULE = $(PROJECT).settings.$(SETTINGS_ENV)
DJANGO_POSTFIX := --settings=$(DJANGO_SETTINGS_MODULE)

ifeq ($(filter $(PROJECT),$(PROJECTS)),)
    $(error A project with name '$(PROJECT)' does not exist. Available projects: $(PROJECTS))
endif

.PHONY: run club migrate msg msg-compile static dumpdata loaddata clean cmd refresh sync deploy check_defined tests

run:
	python -W once manage.py runserver --settings=$(PROJECT).settings.local $(PORT)

club:
	python manage.py runserver --settings=compsciclub_ru.settings.local 8002

shad:
	sudo python manage.py runserver_plus 127.0.0.1:8080 --settings=lk_yandexdataschool_ru.settings.local

tests:
	pytest --create-db --ds=compscicenter_ru.settings.test
	pytest -c compscicenter_ru/pytest.ini --ds=compscicenter_ru.settings.test
	pytest -c compsciclub_ru/pytest.ini --ds=compsciclub_ru.settings.test
	pytest -c lk_yandexdataschool_ru/pytest.ini --ds=lk_yandexdataschool_ru.settings.test
	python manage.py clear_scheduled_jobs

migrate:
	python manage.py migrate $(DJANGO_POSTFIX)

msg:
	python manage.py makemessages -l ru --ignore=public/*

# https://code.djangoproject.com/ticket/24159
# Should set apps in LOCALE_PATHS explicitly until patch been released
msg-compile:
	python manage.py compilemessages --settings=compscicenter_ru.settings.local
	python manage.py compilemessages --settings=compsciclub_ru.settings.local

static:
	python manage.py collectstatic --noinput $(DJANGO_POSTFIX)

dumpdata:
	$(call check_defined, app)
	python manage.py dumpdata $(DJANGO_POSTFIX) --indent=2 $(app) --output=./fixture_$(app).json

loaddata:
	$(call check_defined, src)
	python manage.py loaddata $(DJANGO_POSTFIX) $(src)

clean:
	find . -type f -name "*.py[co]" -print0 -delete
	find . -type f -name "*.mo" -print0 -delete
	find . -type d -name "__pycache__" -print0 -delete
	find . -type f -name "*.DS_Store" -print0 -delete
	-rm -rf htmlcov
	-rm -rf .coverage
	-rm -rf build
	-rm -rf dist
	-rm -rf src/*.egg-info

cmd:
	manage.py $(CMD) $(DJANGO_POSTFIX)

refresh:
	touch $(PROJECT)/*wsgi.py

sync:
	$(call check_defined, app)
	$(call check_defined, conf)
	git pull
	pipenv sync
	python manage.py migrate --settings=$(app).settings.$(conf)
	python manage.py collectstatic  --noinput --settings=$(app).settings.$(conf) --ignore *.map --ignore "webpack-stats-v*.json"

deploy:
	$(call check_defined, app_user)
	git push
	cd ansible && make deploy SITE_USER=$(app_user)

# Check that given variables are set and all have non-empty values,
# die with an error otherwise.
# http://stackoverflow.com/a/10858332/1341309
# Params:
#   1. Variable name(s) to test.
#   2. (optional) Error message to print.
check_defined = \
    $(foreach 1,$1,$(__check_defined))
__check_defined = \
    $(if $(value $1),, \
      $(error Undefined $1$(if $(value 2), ($(strip $2)))))
