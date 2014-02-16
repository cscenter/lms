run:
	python cscsite/manage.py runserver --settings=cscsite.settings.local

syncdb:
	python cscsite/manage.py syncdb --settings=cscsite.settings.local

freeze:
	pip freeze --local > requirements.txt

get-deps:
	pip install -r requirements.txt

dumpdemo:
	python cscsite/manage.py dumpdata --settings=cscsite.settings.local --indent=2 > cscsite/fixtures/demo_data.json

loaddemo:
	python cscsite/manage.py loaddata --settings=cscsite.settings.local cscsite/fixtures/demo_data.json

test:
	python cscsite/manage.py test core index news users textpages learning --settings=cscsite.settings.test
