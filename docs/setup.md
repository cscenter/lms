## Dev setup

 
* Setup python3.4 under virtualenv
* Install system dependencies
```bash
# Fox linux users
sudo apt-get install libjpeg-dev libpng-dev libpq-dev libxml2-dev libxslt1-dev libmagic-dev
# For mac users
brew install libpng libjpeg libpqxx libmagic
```
* Setup PostgreSQL database:

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
* Load data to database from dump
* Create virtualenv for the project and activate it

```bash
# For empty database
$ python cscsite/manage.py syncdb --settings=cscenter.settings.local
```

* To serving static, install grunt with npm locally

```bash
# put grunt cmd in system path
npm install -g grunt-cli
# go to project root dir and install grunt locally
npm install --save-dev grunt load-grunt-tasks grunt-contrib-concat grunt-contrib-uglify grunt-sass grunt-contrib-watch
# to compile scss -> css with libsass
npm install -g node-sass
```
* run dev server 
```
./manage.py runserver --settings=cscenter.settings.local
# or
make
# or
./manage.py gruntserver
```

## Production setup

See [infrastructure](https://github.com/cscenter/site/tree/master/infrastructure) subdirectory.