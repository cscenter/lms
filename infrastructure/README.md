
# TODO (critical):
* separated playbook for cronjobs
* Fix db and media backup cronjob task
* restore db and media/ with playbook
* Add `AbortIncompleteMultipartUpload` Lifecycle rule to cscenter backup bucket.
* `apt-get install ntpd` with servers in /etc/ntp.conf
    server ru.pool.ntp.org
    server pool.ntp.org
    server time.nist.gov
    server ntp.psn.ru
    server ntp1.imvp.ru
* Problems with restarting supervisor. All programs can be in RUNNING state, but ansible task failed. (??? is it fixed?)
* fix certbot default email/domain values! They should be real...
* Remove `unprivileged-binary-patch-arg` from uwsgi ini-file if python3.5 used as system 
`python3` (now py3.6 for ubuntu 14). Also remove `uwsgi` package from requirements/production.txt in that case.
* Problem with restarting supervisor after `Nginx status`
* Think how to update python version without breaking site for updating period (now it does by removing current venv. No idea how to properly rename venv :<)

TODO (important):
* Now `venv` named like `env_35x`. Need to rename them to `venv` back or update playbooks to handle this new name. 
Now only `deploy.yml` edited as a workaround for new naming conv.
* add `registration` app to cscenter, then remove club worker?
* restore db from s3
* add tags. Then use it. E.g. `ansible-playbook -i inventory/ec2.py  provision.yml -v -t lvm` setup lvm only
* Add check for ansible version
* `# Redirect from `www.` to domain without `www` <--- check first that main site domain is two level

Requirements
------------
  
* python3
* Ansible (>=2.4.x) `pip install ansible`
* boto library `pip install boto` (may not work from virtualenv)
* aws cli (optional) `pip install awscli`
* For Dynamic inventory in Ansible used [EC2 external inventory module](http://docs.ansible.com/ansible/intro_dynamic_inventory.html#example-aws-ec2-external-inventory-script)

## Prerequisites

Default VPC, subnets and other network settings except security groups
Manually created:
* Administrator User (with Access Key)
* EC2 KeyPair (don't forget to save in ~/.ssh/)
* Elastic IP (check var in vars/aws.yml)
* S3 buckets. Look for inspiration in `s3` ansible role

Before start
------------

* Install all requirements
* Add Administrator User security credentials (Access Key) to environment, boto or awscli settings
  Ansible uses the boto configuration file (typically ~/.boto) if no credentials are provided
  Also awscli `~/.aws/credentials` works for me:
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
backup_setup.yml | Create users for buckets with appropriate policy configuration. *Works only with Ansible >= 2.0.0*
backup_make.yml | Create backup of media/ folder and db. Should pass `app_user` (cscenter or csclub) and host explicitly (see cmd example below)
backup_restore.yml | Should restore db and media/ folder. But it doesn't work now.
provision.yml | Create security groups. Launch instance. Create additional Volume, attach to new instance. Setup LVM on additional Volume
setup.yml | Part of provision (but can be used independently). Create app on new instance.
deploy.yml | Deploy one of the sites (cscenter or csclub)


## Deploy

* git pull
* install requirements from requirements.txt
* Run django `migrate` command
* Run django `collectstatic` command
* Touch uwsgi configuration to reload app

Command to run:

    ansible-playbook -i inventory/ec2.py deploy.yml --extra-vars "app_user=csclub" -v


Variable `app_user` should be one of [cscenter, csclub]


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

Creates new instance with {{ aws_ec2_host_new }} name tag.

TODO:
* Add fail if instance already exists (max 1 intance with {{ aws_ec2_host_new}} name tag)
* Add new instance to known_hosts (on local machine)
* mv Elastic IP from old instance to new
* tmux create session https://gist.github.com/henrik/1967800 and save them
* symlinks for uwsgi configs to /etc/uwsgi/vassals? 


## Host setup

TODO:
* change zsh settings for csclub (template)
* add tags to additional Volume with `ec2_tag`

* run `ansible-playbook -i inventory/ec2.py setup.yml`. In theory it's idempotent, so you
can modify `setup.yml` and rerun playbook as you wish


## BACKUP restore
Explicitly set host and app_user due to high risk of mix up hosts :<
`ansible-playbook -i inventory/ec2.py backup_restore.yml --extra-vars "app_user=csclub  host=tag_Name_cscweb_new" -vvv`

DB user must be owner `alter database <DB> owner to <db_user>;` and have previligies to createdb and dropdb. `ALTER USER <currentuser> CREATEDB;`
You can temporary set current user as superuser `alter role <db_user> with superuser;`
or you can have a problem with error `must be owner of extension plpgsql`
~~2. pass parameters to command ./manage.py dbrestore --uncompress --backup-extension="psql.gz" --settings=cscenter.settings.local~~

Note: Бэкап делается bd и media. У сайта клуба и центра это общие ресурсы, поэтому нет смысла делать бэкапы и того и другого

TODO:
* Test app write in log
* Restore dbbackup
* Make certbot optional? And add to csclub site too.

## How to replace instance
1. `ansible-playbook -i hosts provision.yml`
2. Manually restore db and media/ for cscenter
3. Change elastic IP
4. Manually stop old instance
5. Replace tag cscweb_new to `cscweb`
NAILED IT!


TIPS:
* syncronize dirs on old and new instance:
```
rsync  -hvrP --ignore-existing --exclude "cache/" ubuntu@52.28.124.90:/home/cscweb/site/repo/cscsite/media/ /shared/media/
```
* dump db
pg_dump -h localhost -U csc cscdb  > cscdb_2408.sql






