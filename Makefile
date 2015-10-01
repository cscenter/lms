SHELL := /bin/sh

PROJECT := cscenter
PORT := 8000
SS := local
DJANGO_SETTINGS_MODULE = $(PROJECT).settings.$(SS)
DJANGO_POSTFIX := --settings=$(DJANGO_SETTINGS_MODULE)

.PHONY: clean coverage test pip static freeze msg msgcompile migrate run dumpdemo loaddemo test_travis lcaomail clean cmd check_defined less_center less_club

run:
	# Sergey Zh: run from cscsite dir due to LOCALE_PATHS settings
	cd cscsite && python manage.py runserver_plus --settings=$(PROJECT).settings.local $(PORT)

migrate:
	python cscsite/manage.py migrate $(DJANGO_POSTFIX)

msg:
	cd cscsite && python manage.py makemessages -l ru
# https://code.djangoproject.com/ticket/24159
# Should set apps in LOCALE_PATHS explicitly until patch been released
msgcompile:
	cd cscsite && python manage.py compilemessages --settings=cscenter.settings.local
	cd cscsite && python manage.py compilemessages --settings=csclub.settings.local

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

test_travis: clean
	python cscsite/manage.py test core index news users learning --settings=$(PROJECT).settings.test_travis

test: clean
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
	python cscsite/manage.py migrate --settings=$(app).settings.$(conf)
	python cscsite/manage.py collectstatic  --noinput --settings=$(app).settings.$(conf)

deploy_remote:
	$(call check_defined, app_user)
	cd infrastructure && ansible-playbook -i inventory/ec2.py deploy.yml --extra-vars "app_user=$(app_user)" -v

less_bootstrap:
	$(eval BS = 1)
	$(call compile_bootstrap, $(BS))

# Experimental: remove after merging with common styles
tmp_less_cm:
	cd cscsite/assets/src/less/; \
	lessc --relative-urls --clean-css="--compatibility=ie8" center/off_canvas_menu.less > ../../css/center/off_canvas_menu.css;

less_center:
	$(call compile_bootstrap, $(BS))
	cd cscsite/assets/src/less/; \
	lessc --relative-urls --clean-css="--compatibility=ie8" center/style.less > ../../css/center/style.css;

less_club:
	$(call compile_bootstrap, $(BS))
	cd cscsite/assets/src/less/; \
	lessc --relative-urls --clean-css="--compatibility=ie8" club/style.less > ../../css/club/style.css;

less: less_center less_club less_bootstrap

# Mac users tip: `brew install fswatch`
less_watch:
	fswatch -o cscsite/assets/src/less/ | xargs -n1 -I{} make less

less_watch_club:
	fswatch -o cscsite/assets/src/less/ | xargs -n1 -I{} make less_club

less_watch_center:
	fswatch -o cscsite/assets/src/less/ | xargs -n1 -I{} make less_center

# Add jasny.bootstrap css here after merging off canvas menu
define compile_bootstrap
	$(if $(BS), cd cscsite/assets/src/less/; \
		lessc --relative-urls --clean-css="--compatibility=ie8" bootstrap.custom.less > ../../css/bootstrap.custom.css;)
endef

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
