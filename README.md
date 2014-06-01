CSC site
========

The power of Django! [![Build Status](https://magnum.travis-ci.com/cscenter/site.svg?token=xBAa4nJZ4qY7pPgbqyTE&branch=master)](https://magnum.travis-ci.com/cscenter/site)

**NOTE**: `libjpeg-dev` and `libpng-dev` should be installed

Installation
============

```
python manage.py syncdb --all --settings=cscsite.settings.local
python manage.py migrate --fake --settings=cscsite.settings.local
python manage.py loaddata --settings=cscsite.settings.local fixtures/demo_data.json
```
