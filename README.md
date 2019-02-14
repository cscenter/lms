# CSC websites

[![Build Status](https://magnum.travis-ci.com/cscenter/site.svg?token=FeohhsTsZzQVU5xBDk5L&branch=master)](https://magnum.travis-ci.com/cscenter/site)

Production stack: AWS, ubuntu 16.04 LTS, nginx, uwsgi, python3.6, Django 2.1.x, postgresql 9.6, redis (for queue), rq workers managed by `systemd`

Section | Description
--- | ---
[about.md](https://github.com/cscenter/site/tree/master/docs/about.md) | For details on architecture and general concerns (april 9, 2015, in Russian).
[setup.md](https://github.com/cscenter/site/tree/master/docs/setup.md) | Some notes about dev and production setup.
[deploy.md](https://github.com/cscenter/site/tree/master/docs/deploy.md) | Deploy easy and fast with ansible 2.x or manually.
[i18n.md](https://github.com/cscenter/site/tree/master/docs/i18n.md) | Notes about translation (in Russian)


#### Snippets

```
# Minimal html to render debug toolbar in django views 
return HttpResponse("<html><body>body tag should be returned</body></html>", content_type='text/html; charset=utf-8')

# Recreate DB
psql -h localhost postgres -c "DROP DATABASE cscdb;"; psql -h localhost postgres -c "CREATE DATABASE cscdb;"; psql -h localhost postgres -c "GRANT ALL privileges ON DATABASE cscdb TO csc;"
psql -h localhost cscdb csc < 
./manage.py changepassword admin
# TODO: update django_site values! ---> write ansible command to fix this

# Enable sql console logger
import logging
from core.utils import SQLFormatter
sql_console_handler = logging.StreamHandler()
sql_console_handler.setLevel(logging.DEBUG)
formatter = SQLFormatter('[%(duration).3f] %(statement)s')
sql_console_handler.setFormatter(formatter)
logger = logging.getLogger('django.db.backends')
logger.addHandler(sql_console_handler)
# Debug queries
logger.removeHandler(sql_console_handler)
```

