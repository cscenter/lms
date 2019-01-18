## Playbooks

See `Makefile` how to run ansible playbooks. But read [Before to start](#before-to-start) first.

#### provison.yml

Launch EC2 instance with `{{ aws_ec2_host }}` tag:Name (configured AWS security groups, additional EBS volume with LVM support and 
backup automation using AWS Lambda).

```bash
make provision
```


#### setup.yml

Part of the provision (but can be used independently). 

* Install and configure system dependencies.
    This actions should be idempotent, so you can modify `setup.yml` and rerun playbook as you wish. 
* Deploys applications to the new instance if `--tags=app-deployment'` provided (application deployment 
    disabled by default since it has a good change to break application)

```bash
make setup
```


#### cs_center.yml / cs_club.yml

Application deployment from the scratch, but can be used partially. See `Makefile` for various deploy actions.


#### deploy.yml

Minimal incremental application deployment workflow.

* git pull
* install requirements from requirements.txt
* Run django `migrate` command
* Run django `collectstatic` command
* Touch uwsgi configuration to reload app

```bash
make deploy app_user=cscenter
```


## Before to start

* Setup configuration manager
    ```bash
    # Python dependencies
    pip3 install ansible boto3 awscli
    # Install vendor roles (see `path_roles` in ansible.cfg)
    ansible-galaxy install -r requirements.yml
    ```

* Add AWS admin credentials to environment, boto or awscli settings
    E.g. `~/.aws/credentials`:
    ```
    [Credentials]
    aws_access_key_id = <your_access_key_here>
    aws_secret_access_key = <your_secret_key_here>
    ```
* Generate EC2 Key Pair and save private key in your `~/.ssh/` directory
* Add generated EC2 SSH key to your SSH agent (e.g., with ssh-add)
* Generate github account access key (with read only credentials) and put files under `files/` directory in `app` role (check working example in target directory)


## TIPS:

* syncronize dirs on an old and new instance:
```
rsync  -hvrP --ignore-existing --exclude "cache/" ubuntu@52.28.124.90:/home/cscweb/site/repo/apps/media/ /shared/media/
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
# Make a db backup from the previous host
ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) --extra-vars "site_user=$(SITE_USER)" backup.yml -v --tags="db"
# Optional (on new instance)
sudo vgrename /dev/vg0 /dev/vg_data
sudo lvrename /dev/vg_data/shared /dev/vg_data/lv_media
# Run setup.yml without ssl
ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_cscsite setup.yml -v --skip-tags="cronjobs" -e "{'enable_https':no}"
# Setup ssl and cronjobs
ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_cscsite setup.yml -v --skip-tags="system-role,cronjobs,lvm-role,db,nginx-role,redis-role" -e "{'enable_https':no}"
```