EC2 provision based on dynamic inventory - [EC2 external inventory module](http://docs.ansible.com/ansible/intro_dynamic_inventory.html#example-aws-ec2-external-inventory-script)

# TODO (critical):
* Do not delete lambda functions logs on recreation
* restore db and media/ with playbook
* Add `AbortIncompleteMultipartUpload` Lifecycle rule to cscenter backup bucket.
* Check that `ntpd` works as expected!
* fix certbot default email/domain values! They should be real...
* Remove `unprivileged-binary-patch-arg` from uwsgi ini-file if python3.6 used as system 
`python3` (now py3.6 for ubuntu 14). Also remove `uwsgi` package from requirements/production.txt in that case.
* Think how to update python version without breaking site for updating period (now it does by removing current venv. No idea how to properly rename venv :<)
* Clear, then warm cache (social_crawler, /alumni and so on)

TODO (important):
* add `registration` app to cscenter, then remove club worker?
* restore db from s3
* Add check for ansible version
* `# Redirect from `www.` to domain without `www` <--- check first that main site domain is two level

Requirements
------------
  
* Ansible (>=2.5.x) `pip install ansible`
* boto3 `pip install boto3` (may not work from virtualenv)
* aws cli (optional) `pip install awscli`

## Prerequisites

Default VPC, subnets and other network settings except security groups
Manually created:
* Administrator User (with Access Key)
* EC2 KeyPair (don't forget to save it in ~/.ssh/)
* Elastic IP
* S3 buckets. Look for inspiration in `s3` ansible role

Before start
------------

* Install all requirements
* Add admin credentials to environment, boto or awscli settings
  E.g. `~/.aws/credentials`:
  ```
  [Credentials]
  aws_access_key_id = <your_access_key_here>
  aws_secret_access_key = <your_secret_key_here>
  ```
* Generate EC2 Key Pair and save private key in your `~/.ssh/` directory
* Add generated EC2 SSH key to your SSH agent (e.g., with ssh-add)
* Generate github account access key (with read only credentials) and put files under `files/` directory in `app` role (check working example in target directory)

Playbooks
---------

File | Action
---- | ------
provision.yml | Create security groups. Launch instance. Create additional Volume, attach to new instance. Setup LVM on additional Volume
setup.yml | Part of provision (but can be used independently). Create app on new instance.
deploy.yml | Deploy routine
backup_make.yml | Create backup of media/ folder and db. Should pass `app_user` (cscenter or csclub) and host explicitly (see cmd example below)


## Deploy

* git pull
* install requirements from requirements.txt
* Run django `migrate` command
* Run django `collectstatic` command
* Touch uwsgi configuration to reload app

Command to run:

    ansible-playbook -i inventory/ec2.py provision.yml -v
    ansible-playbook -i inventory/ec2.py deploy.yml --extra-vars "site_user=csclub" -v


## Create s3 buckets

`ansible-playbook -i hosts backups.yml`

Create users for buckets with appropriate policy configuration.
If users newly created, you can find access keys for them in `files/backup_user_access_keys.txt` under s3 role directory

TODO:
* Create S3 buckets for backups
* Add lifecycle rule for bucket (30 days TTL for now)
* What about logging for buckets? Crypto?
* Add cost allocation tags for buckets (http://docs.aws.amazon.com/AmazonS3/latest/UG/CostAllocationTagging.html)

## Make backup

`ansible-playbook -i inventory/ec2.py backup_make.yml --extra-vars "app_user=cscenter"`

app_user = cscenter | csclub
Don't forget to add ssh-key to ssh agent

## Provision

`ansible-playbook -i hosts provision.yml`

Creates new instance with {{ aws_ec2_host }} name tag.

TODO:
* Add new instance to known_hosts (on local machine)
* mv Elastic IP from old instance to new
* tmux create session https://gist.github.com/henrik/1967800 and save them


## Host setup
```
# In theory it's idempotent, so you can modify `setup.yml` and rerun playbook as you wish
ansible-playbook -i inventory/ec2.py setup.yml
```



## BACKUP restore
Explicitly set host and app_user due to high risk of mix up hosts :<
`ansible-playbook -i inventory/ec2.py backup_restore.yml --extra-vars "app_user=csclub  host=tag_Name_cscweb_new" -vvv`

DB user must be owner `alter database <DB> owner to <db_user>;` and have previligies to createdb and dropdb. `ALTER USER <currentuser> CREATEDB;`
You can temporary set current user as superuser `alter role <db_user> with superuser;`
or you can have a problem with error `must be owner of extension plpgsql`
2. pass parameters to command ./manage.py dbrestore --uncompress --backup-extension="psql.gz" --settings=cscenter.settings.local

Note: Бэкап делается bd и media. У сайта клуба и центра это общие ресурсы, поэтому нет смысла делать бэкапы и того и другого

TODO:
* Test app write in log
* Restore dbbackup

## How to replace instance
1. `ansible-playbook -i hosts provision.yml`
2. Manually restore db and media/ for cscenter
3. Change elastic IP
4. Manually stop old instance


TIPS:
* syncronize dirs on old and new instance:
```
rsync  -hvrP --ignore-existing --exclude "cache/" ubuntu@52.28.124.90:/home/cscweb/site/repo/cscsite/media/ /shared/media/
```
* dump db
pg_dump -h localhost -U csc cscdb  > cscdb_2408.sql
* To pass boolean value with extra vars to playbook use this form `-e "{'var_name':yes}"`

```
# Show all available LVM volumes
sudo lvscan
# Disk stats
df -h
```




# Update cronjobs
ansible-playbook -i inventory/ec2.py setup.yml --tags="cronjobs"



# Как пересоздать машину

* TODO: Ставим заглушку на основном сайте, чтобы не было изменений с начала пересоздания машины.
* Создаём свежий бэкап диска, на котором хранится папка media/ Добавляем ему необходимые теги. Смотри task `ec2_vol` в `provision.yml`
* Делаем бэкап БД. Смотри команду `make dbbackup`

Note: Кластер postgresql по идее лежит тоже на диске рядом с `media/` и можно было бы попробовать переиспользовать его, 
но сейчас БД создаётся с нуля, этот сценарий универсальный и подходит для машин без дополнительного диска.

* Если есть предыдущий snapshot и зачем-то поменяли vg/lv name, то меняем их вручную, иначе просто затрём весь диск

```
sudo vgrename /dev/vg0 /dev/vg_data
# Rename `shared` to `lv_media` in `vg_data` volume group
sudo lvrename /dev/vg_data/shared /dev/vg_data/lv_media
```

* В файле `Makefile` указываем тег новой машины. В provision.yml выставляем переменную `aws_ec2_prev_host_tag` равной тегу предыдущей машины. 
Тогда диск для media/ будет создан из сделанного ранее снепшота.

TODO: из cronjobs удалить создание media/ ?

* Запускаем `setup.yml` без установки ssl. Т.к. домен не связан с новой машиной мы не сможем подтвердить право владения.
* Руками восстанавливаем дамп БД :< При этом её лучше удалить, т.к. после джанговских migrate как-то не оч идёт восстановление

```
sudo -u postgres psql
    DROP DATABASE cscdb;
    CREATE DATABASE cscdb;
    GRANT ALL privileges ON DATABASE cscdb TO csc;
```

* Если всё ок, перенаправляем поток на новую машину и запускаем уже с установкой сертификатов

FIXME: как избежать downtime'а тут? Копировать сертификаты со старой машины??







```
AWS_EC2_INSTANCE_TAG := cscsite
SITE_USER := cscenter
make provision
# Make db backup from prev host
ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) --extra-vars "site_user=$(SITE_USER)" dbbackup.yml -v
# Optional (on new instance)
sudo vgrename /dev/vg0 /dev/vg_data
sudo lvrename /dev/vg_data/shared /dev/vg_data/lv_media
# Run setup.yml without ssl
ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_cscsite setup.yml -v --skip-tags="cronjobs" -e "{'enable_https':no}"
# Setup ssl and cronjobs
ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_cscsite setup.yml -v --skip-tags="system-role,cronjobs,lvm-role,db,nginx-role,redis-role" -e "{'enable_https':no}"
```