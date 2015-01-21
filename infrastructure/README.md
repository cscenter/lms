# Provisioning and deployment of CSC site

## Credentials

* you need to obtain `csc-main.pem` and AWS credentials (from someone)
* add SSH keys to your SSH agent with `ssh-add csc-main.pem`
* put AWS credentials to `~/.boto` as follows:
```
[Credentials]
aws_access_key_id = <your_access_key_here>
aws_secret_access_key = <your_secret_key_here>
```
* SSH key for host with deployment rights is in
`files/cscweb_deploy_ssh_key{,.pub}`. It's OK because one presumable have an
access to the repository already

## Prerequisites

* recent Ansible (1.8.2 at the point of writing)
* globally installed [boto](https://github.com/boto/boto) (may not work from
virtualenv)

## Provisioning

* run `ansible-playbook provision.yml`
* now you should have EC2 VMs set up, IP is displayed by a playbook
* to SSH into the node: `ssh ubuntu@IP-THAT-HAS-BEEN-SHOWN-BY-PLAYBOOK`
* host setup runs automatically after provisioning, no need to call it separately

## Host setup

* run `ansible-playbook -i ec2.py setup.yml`. In theory it's idempotent, so you
can modify `setup.yml` and rerun playbook as you wish

**NOTE:** it is hard to keep changes in playbook and on remote server in
  sync. Please try to avoid editing remote configs directly, aiming for
  idempotent playbook instead.
