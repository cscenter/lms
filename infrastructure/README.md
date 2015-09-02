
# TODO (critical):
* install and configure memcached
* restore db and media/ with playbook


TODO (important):
* restore db from s3
* deploy for cscenter and csclub
* change uwsgi process groups to `shared` if u need ability to change files from every site. Or update django upload behaviour
* add tags. Then use it. E.g. `ansible-playbook -i inventory/ec2.py  provision.yml -v -t lvm` setup lvm only

Requirements
------------
  
* python
* Ansible (>=2.0.0a for s3 role if needed) `pip install ansible`
* boto library `pip install boto` (may not work from virtualenv)
* aws cli (optional) `pip install awscli`
* For Dynamic inventory in Ansible used [EC2 external inventory module](http://docs.ansible.com/ansible/intro_dynamic_inventory.html#example-aws-ec2-external-inventory-script)

## Prerequisites

Default VPC, subnets and other network settings except security groups
Manually created:
* Administrator User (with Access Key)
* EC2 KeyPair (don't forget to save in ~/.ssh/)
* Elastic IP (check var in vars/aws.yml)
* S3 buckets. Look for inspiration in `s3` ansible role (needs Ansible >= 2.0.0)

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
* Generate TLS certificate and put files under `files/` directory in `app` role (Current TLS cert is valid until **January 27 2016**) (check working example in target directory)

Playbooks
---------

File | Action
---- | ------
backup_setup.yml | Create users for buckets with appropriate policy configuration. *Works only with Ansible >= 2.0.0*
backup_make.yml | Create backup of media/ folder and db. Should pass `app_user` (cscenter or csclub) and host explicitly (see cmd example below)
backup_restore.yml | Should restore db and media/ folder. But it doesn't work now.
provision.yml | Create security groups. Launch instance. Create additional Volume, attach to new instance. Setup LVM on additional Volume
setup.yml | Part of provision (but can be used independently). Create app on new instance.



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
~~2. pass parameters to command cscsite/manage.py dbrestore --uncompress --backup-extension="psql.gz" --settings=cscenter.settings.local~~

Note: Бэкап делается bd и media. У сайта клуба и центра это общие ресурсы, поэтому нет смысла делать бэкапы и того и другого

TODO:
* Test app write in log
* Restore dbbackup

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






