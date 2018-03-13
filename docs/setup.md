## Dev setup

 
* Install python3.4, pip3, virtualenv
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
postgres=# CREATE DATABASE test_cscdb;
CREATE DATABASE
postgres=# ALTER DATABASE test_cscdb OWNER TO csc;
ALTER DATABASE
postgres=# ALTER USER csc with CREATEDB;
ALTER ROLE
^D
```
* Load data to database from dump
```bash
# If you want empty database by any reason, don't forget to run migrations
$ python cscsite/manage.py migrate --settings=cscenter.settings.local
```
* Create virtualenv for the project and activate it


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
# or run make cmd from project root dir
make
# or
./manage.py gruntserver
```

## Production setup

See [infrastructure](https://github.com/cscenter/site/tree/master/infrastructure) subdirectory.