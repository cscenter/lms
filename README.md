CSC site
========

The power of Django! [![Build Status](https://magnum.travis-ci.com/cscenter/site.svg?token=xBAa4nJZ4qY7pPgbqyTE&branch=master)](https://magnum.travis-ci.com/cscenter/site)

**NOTE**: `libjpeg-dev`, `libpng-dev` and `libpq-dev` should be installed

Dev installation
================

* setup python2, pip, virtualenv `libjpeg-dev`, `libpng-dev` and `libpq-dev` globally;
* create virtualenv for the project and open it;
* setup PostgreSQL database:

```bash
> sudo -u postgres psql
[sudo] password for user:
psql (9.4.1)
Type "help" for help.

postgres=# CREATE DATABASE cscdb;
CREATE DATABASE
postgres=# CREATE USER csc WITH password 'FooBar';
CREATE ROLE
postgres=# GRANT ALL privileges ON DATABASE cscdb TO csc;
GRANT
^D
```

* do the Django part of the database configuration:

```bash
$ python cscsite/manage.py syncdb --settings=cscsite.settings.local
```

* run with `python manage.py runserver --settings=cscsite.settings.local`

Production setup
===============

See [infrastructure](https://github.com/cscenter/site/tree/master/infrastructure) subdirectory.


Misc
====

To test:

```
pip install gorun
gorun.py gorun_settings.py
```
