## Production deploy

#### Ansible 2.x

Add aws credentials to ~/.aws/credentials. Then run:

    make deploy app_user=cscenter

#### Manual

To simplify the process, production host's ssh key is
set as "deploy key" on github, so one can `git pull` the code from
production. Common workflow is as follows (example for `cscenter` site, 
for club site use `csclub` username):

```
ssh ubuntu@compscicenter.ru
sudo su cscenter
cd ~/site/repo
git pull
pip install -r requirements.txt
./manage.py migrate --settings=cscenter.settings.production
./manage.py collectstatic --noinput --settings=cscenter.settings.production
# Activate ubuntu user
exit
# Reload uwsgi related processes
sudo touch /etc/uwsgi/vassalse/cscenter.ini
```

Some notes:
* `ssh ubuntu@compscicenter.ru`. You can ask Sergei Lebedev or Ekaterina
Lebedeva to add your key into `authorized_keys`;
* You can use `tmux` also. See [cheatsheet](http://www.dayid.org/os/notes/tm.html) 
for shortcuts (most used ones
are `^b n`/`^b p` to switch "tabs", `^b c` to create tab and `^b d` to "detach",
where `^b` is `ctrl+b`). For a bit better security, web-related stuff is done by
a separate non-sudoers user `cscenter` or `csclub`, so it's handy to 
have two separate "tabs" in tmux.
* Don't forget to clear sometimes static folder with `--clear` option
* Note that uwsgi reload is needed
to reload translation, static file update (see
[ManifestStaticFilesStorage docs](https://docs.djangoproject.com/en/1.9/ref/contrib/staticfiles/#django.contrib.staticfiles.storage.ManifestStaticFilesStorage)
for details) and python modules, so you will need to reload uwsgi on almost
every update.