SHELL := /bin/sh

AWS_EC2_INSTANCE_TAG := cscsite
SITE_USER := cscenter
PLAYBOOK_NAME := cs_center

.PHONY: deploy provision setup cronjobs

deploy:
	ansible-playbook -i inventory/ec2.py deploy.yml -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) --extra-vars "site_user=$(SITE_USER)" -v

dbbackup:
	ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) --extra-vars "site_user=$(SITE_USER)" backup.yml -v --tags="db"

mediabackup:
	ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) --extra-vars "site_user=$(SITE_USER)" backup.yml -v --tags="media"

provision:
	ansible-playbook -i hosts -e aws_ec2_instance_tag=$(AWS_EC2_INSTANCE_TAG) provision.yml -v

setup:
	ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) setup.yml -v --tags="app-deployment"

# Use `update-app-*` commands after full application setup
update-app-cronjobs:
	ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) $(PLAYBOOK_NAME).yml --tags="cronjobs" -v

update-app-nginx-config:
	ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) $(PLAYBOOK_NAME).yml --tags="nginx" -v

update-app-uwsgi-config:
	ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) $(PLAYBOOK_NAME).yml --tags="uwsgi" -v
