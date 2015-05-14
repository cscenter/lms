run:
	# Sergey Zh: run from cscsite dir due to LOCALE_PATHS settings
	cd cscsite && python manage.py runserver --settings=cscsite.settings.local

syncdb:
	python cscsite/manage.py syncdb --settings=cscsite.settings.local

msg:
	cd cscsite && python manage.py makemessages -l ru
	
msgcompile:
	cd cscsite && python manage.py compilemessages

static:
	cd cscsite && python manage.py collectstatic --noinput --settings=cscsite.settings.production

freeze:
	pip freeze --local > requirements.txt

get-deps:
	pip install -r requirements.txt

dumpdemo:
	python cscsite/manage.py dumpdata --settings=cscsite.settings.local --indent=2 > cscsite/fixtures/demo_data.new.json

loaddemo:
	python cscsite/manage.py loaddata --settings=cscsite.settings.local cscsite/fixtures/demo_data.json

test:
	python cscsite/manage.py test core index news users textpages learning --settings=cscsite.settings.test

test_nocoverage:
	python cscsite/manage.py test core index news users textpages learning --settings=cscsite.settings.test_nocover

init:
	python cscsite/manage.py syncdb --all --settings=cscsite.settings.local
	python cscsite/manage.py migrate --fake --settings=cscsite.settings.local
	python cscsite/manage.py loaddata --settings=cscsite.settings.local cscsite/fixtures/demo_data.json

stylecheck:
	pep8 cscsite/users cscsite/index cscsite/news cscsite/learning cscsite/textpages cscsite/core --exclude=migrations
#PYTHONPATH=cscsite pylint -rn --load-plugins pylint_django --rcfile=pylint.config learning core

localmail:
	python -m smtpd -n -c DebuggingServer localhost:1025
