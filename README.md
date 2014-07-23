CSC site
========

The power of Django! [![Build Status](https://magnum.travis-ci.com/cscenter/site.svg?token=xBAa4nJZ4qY7pPgbqyTE&branch=master)](https://magnum.travis-ci.com/cscenter/site)

**NOTE**: `libjpeg-dev` and `libpng-dev` and `libmysqlclient-dev` should be installed

Installation
============

Setup MySQL database:

```bash
$ mysql -u root -p
> CREATE DATABASE cscdb CHARACTER SET utf8;
> CREATE USER 'csc'@'localhost' IDENTIFIED BY 'FooBar';
> GRANT ALL ON cscdb.* TO 'csc'@'localhost';
^D
```

Do the Django part of the database configuration:

```bash
$ python cscsite/manage.py syncdb --all --settings=cscsite.settings.local
$ python cscsite/manage.py migrate --settings=cscsite.settings.local --no-initial-data
```
