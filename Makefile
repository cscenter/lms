run:
	python cscsite/manage.py runserver --settings=cscsite.settings.local

freeze:
	pip freeze --local > requirements.txt

get-deps:
	pip install -r requirements.txt
