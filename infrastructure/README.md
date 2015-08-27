* change uwsgi process groups to `shared` if u need ability to change files everywhere (created from center site on club site, e.g.)

TODO:
* restore db from s3
* deploy for cscenter and csclub
* create volume with lvm and other shit
* smthng wrong with apt-get upgrade/ apt-get update...
* init Django db. No matter club or center user here] CHECKKKKK

Requirements
------------
  
* python
* Ansible (>=2.0.0a) `pip install ansible`
* boto library `pip install boto` (may not work from virtualenv)
* aws cli (optional) `pip install awscli`
* For Dynamic inventory in Ansible used [EC2 external inventory module](http://docs.ansible.com/ansible/intro_dynamic_inventory.html#example-aws-ec2-external-inventory-script)

## Prerequisites

We are using default VPC, subnets and other network settings except security groups
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
* Add EC2 SSH key (KeyPair from Prerequisites) to your SSH agent (e.g., with ssh-add)
* Generate github account access key (with read only credentials) and put files under `files/` directory
* Generate TLS certificate and put files under `files/` directory (Current TLS cert is valid until **January 27 2016**)

Playbooks
---------

File | Action
---- | ------
backup_setup.yml | Create users for buckets with appropriate policy configuration. *Works only with Ansible >= 2.0.0*
provision.yml | Create security groups. Launch instance. Create additional Volume, attach to new instance. Setup LVM on additional Volume
backup_make.yml | Create backup of media/ folder and db. Should pass `app_user` (cscenter or csclub) and host explicitly (see cmd example below)



## S3 Role

`ansible-playbook -i hosts backups.yml`

Create users for buckets with appropriate policy configuration.
If users newly created, you can find access keys for them in `files/backup_user_access_keys.txt` under s3 role directory

TODO:
* Create S3 buckets for backups
* Add lifecycle rule for bucket (30 days TTL for now)
* Think about logging for buckets (Is it free?)
* Add cost allocation tags for buckets (http://docs.aws.amazon.com/AmazonS3/latest/UG/CostAllocationTagging.html)

# Make backup
`ansible-playbook -i inventory/ec2.py backup_make.yml --extra-vars "app_user=cscenter"`
app_user = cscenter | csclub
Don't forget to add ssh-key to ssh agent


## Provision Role

`ansible-playbook -i hosts provision.yml`

TODO:
* Add new instance to known_hosts.
* backups, stop old instance and run new one
* mv Elastic IP from old instance to new
* tmux create session https://gist.github.com/henrik/1967800 and save them
* symlinks for uwsgi configs to /etc/uwsgi/vassals? 


## Host setup

TODO:
* change zsh settings for csclub (e.g. template)
* mount new Volume (fstab, lvm). Share with
* Add new instance ip to known hosts
* add tags to additional Volume with `ec2_tag`

* run `ansible-playbook -i inventory/ec2.py setup.yml`. In theory it's idempotent, so you
can modify `setup.yml` and rerun playbook as you wish


## BACKUP restore
Explicitly set host and app_user due to high risk of mix up hosts :<
`ansible-playbook -i inventory/ec2.py backup_restore.yml --extra-vars "app_user=csclub  host=tag_Name_cscweb_new" -vvv`

* Test app write in log
* Permissions in media/ folder! Check. DOUBLE CHECK.
* Restore dbbackup

# How to:

## Replace instance
1. `ansible-playbook -i hosts provision.yml`
2. `ansible-playbook -i inventory/ec2.py setup.yml`
3. backup restore for cscenter
4. Вот тут по идее нужно будет поставить заглушку. Снять актуальный бэкап БД (прямо на хосте). Его залить на новую машину. И установить. После этого перевести elastic ip на новую машину
5. Затестить всё.
4. Manually stop old instance
5. Replace tag cscweb_new to `cscweb`
NAILED IT!

Note: Бэкап делается bd и media. У сайта клуба и центра это общие ресурсы, поэтому нет смысла делать бэкапы и того и другого
* Как быть с правами создаваемых файлов в папке media?

rsync  -hvrP --ignore-existing --exclude "cache/" ubuntu@52.28.124.90:/home/cscweb/site/repo/cscsite/media/ /shared/media/

# TAGS

ТУДУ:
`ansible-playbook -i inventory/ec2.py  provision.yml -v -t lvm` setup lvm only



pg_dump -h localhost -U csc cscdb  > cscdb_2408.sql


## How to restore DB and media/ files
alter role my_user_name with superuser;
or you will be have a problem with error `must be owner of extension plpgsql`


user must be owner of db `alter database <DB> owner to <currentuser>;`
1. Create user with previligies to createdb and dropdb or temporary grant current user preveligies `ALTER USER <currentuser> CREATEDB;`
2. pass parameters to command cscsite/manage.py dbrestore --uncompress --backup-extension="psql.gz" --settings=cscenter.settings.local


cscsite/manage.py dbrestore --uncompress --backup-extension="psql.gz" --settings=cscenter.settings.local