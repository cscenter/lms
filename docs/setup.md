## Dev setup

* Install system dependencies
```bash
# Fox linux users
sudo apt-get install libjpeg-dev libpng-dev libpq-dev libxml2-dev libxslt1-dev libmagic-dev
# For mac users
brew install libpng libjpeg libpqxx libmagic
# Install pycurl on Mac OS
brew install curl --with-openssl
PYCURL_SSL_LIBRARY=openssl LDFLAGS="-L/usr/local/opt/openssl/lib -L/usr/local/opt/curl/lib" CPPFLAGS="-I/usr/local/opt/openssl/include -I/usr/local/opt/curl/include" pip install --no-cache-dir pycurl

```
* Login to postgres client:

```bash
sudo -u postgres psql
# On Mac OS
psql postgres
```

And setup postgres databases:

```sql
CREATE DATABASE cscdb;
CREATE USER csc WITH password 'FooBar';
GRANT ALL privileges ON DATABASE cscdb TO csc;

CREATE DATABASE test_cscdb;
ALTER DATABASE test_cscdb OWNER TO csc;
ALTER USER csc with CREATEDB;
```

* Create virtualenv for the project, activate it and install all python dependencies with pipenv (see Pipenv.lock in the root dir)

* Run migrations
```bash
# Or simply generate an empty database
$ python manage.py migrate --settings=compscicenter_ru.settings.local
```

* Create `.env` file and place it under `compscicenter_ru/settings/` directory. The easiest way is to copy and rename `.env.example` which could be find in the target directory.




## Production setup

See [infrastructure](https://github.com/cscenter/site/tree/master/infrastructure) subdirectory.