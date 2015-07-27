Computer Science Center/Club websites
=====================================

ADD apt-get install gettext TO `infrastructure`

[![Build Status](https://magnum.travis-ci.com/cscenter/site.svg?token=FeohhsTsZzQVU5xBDk5L&branch=master)](https://magnum.travis-ci.com/cscenter/site)

Dev setup
---------

* setup python2, pip, virtualenv `libjpeg-dev`, `libpng-dev` and `libpq-dev` globally;
    note for mac users: `brew intall libpng libjpeg libpqxx`
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
$ python cscsite/manage.py syncdb --settings=cscenter.settings.local
```

* load data for menu with `python cscsite/manage.py loaddata` from cscsite/fixtures/ folder

* run with `python manage.py runserver --settings=cscenter.settings.local`


Production setup
----------------

See [infrastructure](https://github.com/cscenter/site/tree/master/infrastructure) subdirectory.


Production deploy
-----------------

Right now it's done manually (it's probably better to leave it so until staging
environment is set up). To simplify the process, production host's ssh key is
set as "deploy key" on github, so one can `git pull` the code from
production. Common workflow is as follows:

* `ssh ubuntu@compscicenter.ru`. You can ask Sergei Lebedev or Ekaterina
Lebedeva to add your key into `authorized_keys`;
* `tmux attach`. Tmux is used on the server, please consult
[cheatsheet](http://www.dayid.org/os/notes/tm.html) for shorcuts (most used ones
are `^b n`/`^b p` to switch "tabs", `^b c` to create tab and `^b d` to "detach",
where `^b` is `ctrl+b`). For a bit better security, web-related stuff is done by
a separate non-sudoers user `cscweb`, so it's handy to have two separate "tabs"
in tmux: one with `sudo su - cscweb` (this will "switch" the tab to `cscweb`
user) and other with `ubuntu` user;
* `git pull` in `cscweb` "tab", optionally followed by

always run `./manage.py compilemessages --settings=cscenter.settings.production`

then

```
./manage.py migrate MIGRATED_APP --settings=cscenter.settings.production
```

or

```
./manage.py collectstatic --noinput --settings=cscenter.settings.production
```

or 

```
pip install -r requirements.txt
```

Don't forget to clear sometimes static folder with `--clear` option

* `sudo service uwsgi reload` in `ubuntu` tab. Note that uwsgi reload is needed
to reload translation, static file update (see
[ManifestStaticFilesStorage docs](https://docs.djangoproject.com/en/1.7/ref/contrib/staticfiles/#django.contrib.staticfiles.storage.ManifestStaticFilesStorage)
for details) and python modules, so you will need to reload uwsgi on almost
every update.


Misc
----

Add `less-plugin-clean-css` plugin for less to minify output version.
See `less` command in Makefile for details how to use it.

To autorun test on change:

```
pip install gorun
gorun.py gorun_settings.py
```

For details on architecture and general concerns, see
[about.md](https://github.com/cscenter/site/tree/master/about.md) (in Russian).

TODO:

* Create make cmd for less