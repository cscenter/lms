run:
	python cscsite/manage.py runserver --settings=cscsite.settings.local

syncdb:
	python cscsite/manage.py syncdb --settings=cscsite.settings.local

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

stylecheck:
	pep8 cscsite/users cscsite/index cscsite/news cscsite/learning cscsite/textpages cscsite/core
	PYTHONPATH=cscsite pylint -rn --load-plugins pylint_django --rcfile=pylint.config learning core
