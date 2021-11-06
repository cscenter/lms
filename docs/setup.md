## Dev setup

* Install system dependencies
```bash
# Fox linux users
sudo apt-get install libjpeg-dev libpng-dev libpq-dev libxml2-dev libxslt1-dev libmagic-dev
# For mac users
brew install libpng libjpeg libpqxx libmagic swig
# Install libraries that depend on openssl
brew install curl-openssl
PYCURL_SSL_LIBRARY=openssl LDFLAGS="-L/usr/local/opt/openssl@1.1/lib -L/usr/local/opt/curl-openssl/lib" CPPFLAGS="-I/usr/local/opt/openssl@1.1/include -I/usr/local/opt/curl-openssl/include" pip install --compile --no-cache-dir pycurl
LDFLAGS="-L$(brew --prefix openssl)/lib" CFLAGS="-I$(brew --prefix openssl)/include" SWIG_FEATURES="-cpperraswarn -includeall -I$(brew --prefix openssl)/include" pip install m2crypto
# for fish shell
env PYCURL_SSL_LIBRARY=openssl LDFLAGS="-L"(brew --prefix openssl)"/lib -L/usr/local/opt/curl-openssl/lib" CPPFLAGS="-I"(brew --prefix openssl)"/include -I/usr/local/opt/curl-openssl/include" pip install --compile --no-cache-dir pycurl
env LDFLAGS="-L"(brew --prefix openssl)"/lib" CFLAGS="-I"(brew --prefix openssl)"/include" SWIG_FEATURES="-cpperraswarn -includeall -I"(brew --prefix openssl)"/include" pip install m2crypto

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
ALTER USER csc with CREATEDB;
GRANT ALL privileges ON DATABASE cscdb TO csc;
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
