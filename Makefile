SHELL := /bin/sh

PROJECT := cscenter
SS := local
DJANGO_SETTINGS_MODULE = $(PROJECT).settings.$(SS)
DJANGO_POSTFIX := --settings=$(DJANGO_SETTINGS_MODULE)

.PHONY: clean coverage test pip static freeze msg msgcompile migrate run dumpdemo loaddemo test_travis lcaomail clean cmd check-app-specified check-src-specified

run:
	# Sergey Zh: run from cscsite dir due to LOCALE_PATHS settings
	cd cscsite && python manage.py runserver $(DJANGO_POSTFIX)

migrate:
	python cscsite/manage.py migrate $(DJANGO_POSTFIX)

msg:
	cd cscsite && python manage.py makemessages -l ru
	
msgcompile:
	cd cscsite && python manage.py compilemessages

static:
	cd cscsite && python manage.py collectstatic --noinput $(DJANGO_POSTFIX)

freeze:
	pip freeze --local > requirements.txt

pip:
	pip install -r requirements.txt

dumpdemo: check-app-specified
	python cscsite/manage.py dumpdata $(DJANGO_POSTFIX) --indent=2 $(app) --output=./fixture_$(app).json

loaddemo: check-src-specified
	python cscsite/manage.py loaddata $(DJANGO_POSTFIX) $(SRC)

coverage:
	python cscsite/manage.py test core index news users learning --settings=$(PROJECT).settings.test

test_travis:
	python cscsite/manage.py test core index news users learning --settings=$(PROJECT).settings.test_travis

test:
	python cscsite/manage.py test core index news users learning --settings=$(PROJECT).settings.test_nocover

localmail:
	python -m smtpd -n -c DebuggingServer localhost:1025

clean:
	find . -name "*.pyc" -print0 -delete
	-rm -rf htmlcov
	-rm -rf .coverage
	-rm -rf build
	-rm -rf dist
	-rm -rf src/*.egg-info

cmd:
	cscsite/manage.py $(CMD) $(DJANGO_POSTFIX)

# Prerequisite
check-app-specified:
	ifndef app
	    $(error APP is undefined)
	endif

check-src-specified:
	ifndef src
	    $(error src is undefined)
	endif