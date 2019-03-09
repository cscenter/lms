SHELL := /bin/sh

AWS_EC2_INSTANCE_TAG := cscsite
SITE_USER := cscenter
PLAYBOOK_NAME := cs_center

.PHONY: deploy provision setup

deploy:
	ansible-playbook -i inventory/ec2.py deploy.yml -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) --extra-vars "site_user=$(SITE_USER)" -v

provision:
	ansible-playbook -i hosts -e aws_ec2_instance_tag=$(AWS_EC2_INSTANCE_TAG) provision.yml -v

setup-vm:
	ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) setup.yml -v
# Setup VM and all site applications
setup:
	ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) setup.yml -v --tags="app-deployment"

backup-db:
	ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) --extra-vars "site_user=$(SITE_USER)" backup.yml -v --tags="db"

backup-media:
	ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) --extra-vars "site_user=$(SITE_USER)" backup.yml -v --tags="media"

# Use `update-app-*` commands after full application setup
# --skip-tags="nginx-role" should increase playbook speed by avoiding checking dependent roles, but each command finally have to be idempotent without skipping any tag.
update-app-cronjobs:
	ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) $(PLAYBOOK_NAME).yml --tags="cronjobs" --skip-tags="nginx-role" -v

update-app-nginx-config:
	ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) $(PLAYBOOK_NAME).yml --tags="nginx" --skip-tags="nginx-role" -v

update-app-uwsgi-config:
	ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) $(PLAYBOOK_NAME).yml --tags="uwsgi" --skip-tags="nginx-role" -v

# FIXME: Generate certificates use `creates` which doesn't depend on domain list. Even with hash check it could be broken when needs to add `--expand` key
update-app-certificate:
	ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) $(PLAYBOOK_NAME).yml --tags="certbot" --skip-tags="nginx-role" -v

dev-setup:
	ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_dev_csc setup.yml -v --skip-tags="cronjobs,lvm-role" -e "{'enable_https':no}" --tags="compscicenter.ru"