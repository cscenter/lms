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

## Prerequisites

* recent Ansible (1.8.2 at the point of writing)
* globally installed [boto](https://github.com/boto/boto) (may not work from virtualenv)

## Provisioning

* run `ansible-playbook provision.yml`
* now you should have EC2 VMs set up, IP is displayed by a playbook
* to SSH into the node: `ssh ubuntu@IP-THAT-HAS-BEEN-SHOWN-BY-PLABOOK`

## Host setup

* run `ansible -i ec2.py -u ubuntu tag_Name_cscweb -m ping`
