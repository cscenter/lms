SHELL := /bin/sh

PROJECT := cscenter
PORT := 8000
SS := local
DJANGO_SETTINGS_MODULE = $(PROJECT).settings.$(SS)
DJANGO_POSTFIX := --settings=$(DJANGO_SETTINGS_MODULE)

.PHONY: clean coverage test pip static freeze msg msgcompile migrate run dumpdemo loaddemo test_travis lcaomail clean cmd check_defined sass sass_club webpack run_club

run:
	python manage.py runserver_plus --settings=$(PROJECT).settings.local $(PORT)

migrate:
	python manage.py migrate $(DJANGO_POSTFIX)

msg:
	python manage.py makemessages -l ru
# https://code.djangoproject.com/ticket/24159
# Should set apps in LOCALE_PATHS explicitly until patch been released
msgcompile:
	python manage.py compilemessages --settings=cscenter.settings.local
	python manage.py compilemessages --settings=csclub.settings.local

static:
	python manage.py collectstatic --noinput $(DJANGO_POSTFIX)

freeze:
	pip freeze --local > requirements.txt

pip:
	pip install -r requirements.txt

dumpdemo:
	$(call check_defined, app)
	python manage.py dumpdata $(DJANGO_POSTFIX) --indent=2 $(app) --output=./fixture_$(app).json

loaddemo:
	$(call check_defined, src)
	python manage.py loaddata $(DJANGO_POSTFIX) $(src)

coverage:
	python manage.py test core index news users learning --settings=$(PROJECT).settings.test

test_travis: clean
	python manage.py test core index news users learning --settings=$(PROJECT).settings.test_travis

test: clean
	python manage.py test core index news users learning --settings=$(PROJECT).settings.test

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
	manage.py $(CMD) $(DJANGO_POSTFIX)

refresh:
	touch $(PROJECT)/*wsgi.py

deploy:
	$(call check_defined, app)
	$(call check_defined, conf)
	git pull
	pip install -r requirements.txt
	python manage.py migrate --settings=$(app).settings.$(conf)
	python manage.py collectstatic  --noinput --settings=$(app).settings.$(conf)

deploy_remote:
	$(call check_defined, app_user)
	git push
	cd infrastructure && ansible-playbook -i inventory/ec2.py deploy.yml --extra-vars "app_user=$(app_user)" -v

sass:
	cd cscsite/assets/; node-sass -w src/sass/center/style.scss css/center/style.css

sass_club:
	cd cscsite/assets/; node-sass -w src/sass/club/style.scss css/club/style.css

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
