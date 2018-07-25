SHELL := /bin/sh

AWS_EC2_INSTANCE_TAG := cscsite
SITE_USER := cscenter

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
	ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) setup.yml -v

cronjobs:
	ansible-playbook -i inventory/ec2.py -e aws_ec2_host=tag_Name_$(AWS_EC2_INSTANCE_TAG) setup.yml --tags="cronjobs"
