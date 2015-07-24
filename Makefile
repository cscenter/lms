SHELL := /bin/sh

PROJECT := cscenter
SS := local
DJANGO_SETTINGS_MODULE = $(PROJECT).settings.$(SS)
DJANGO_POSTFIX := --settings=$(DJANGO_SETTINGS_MODULE)

.PHONY: clean coverage test pip static freeze msg msgcompile migrate run dumpdemo loaddemo test_travis lcaomail clean cmd check_defined

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

dumpdemo:
	$(call check_defined, app)
	python cscsite/manage.py dumpdata $(DJANGO_POSTFIX) --indent=2 $(app) --output=./fixture_$(app).json

loaddemo:
	$(call check_defined, src)
	python cscsite/manage.py loaddata $(DJANGO_POSTFIX) $(src)

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

refresh:
	touch $(PROJECT)/*wsgi.py

deploy:
	$(call check_defined, app)
	$(call check_defined, conf)
	git pull
	pip install -r requirements.txt
	python cscsite/manage.py compilemessages --settings=$(app).settings.$(conf)
	python cscsite/manage.py migrate --settings=$(app).settings.$(conf)
	python cscsite/manage.py collectstatic --settings=$(app).settings.$(conf)

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
