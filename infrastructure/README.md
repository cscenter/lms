# Provisioning and deployment of CSC site

## AWS setup

This is already done for you and provided here for documentation purposes
because it was done by hand (as opposed to automatic provisioning by scripts or
playbooks).

* user for provisioning should be provided
* they should be granted rights neccessary for provisioning of nodes
* S3 bucket for backups should be created
* additional user which only can read and write to the bucket should be created

IAM policy for the "backup" user:

```
{
  "Statement": [
    {
      "Sid": "Stmt1422269318537",
      "Action": [
        "s3:DeleteObject",
        "s3:GetObject",
        "s3:GetObjectAcl",
        "s3:PutObject",
        "s3:PutObjectAcl"
      ],
      "Effect": "Allow",
      "Resource": "arn:aws:s3:::csc-main-backup/*"
    },
    {
      "Sid": "Stmt1422269334760",
      "Action": [
        "s3:ListBucket"
      ],
      "Effect": "Allow",
      "Resource": "arn:aws:s3:::csc-main-backup"
    }
  ]
}
```


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
* both could be installed globally from pip

## Provisioning

* run `ansible-playbook provision.yml`
* do not forget to accept an SSH fingerprint of new VM
* now you should have EC2 VMs set up, IP is displayed by a playbook
* to SSH into the node: `ssh ubuntu@IP-THAT-HAS-BEEN-SHOWN-BY-PLAYBOOK`
* host setup runs automatically after provisioning, no need to call it separately

## Host setup

* run `ansible-playbook -i ec2.py setup.yml`. In theory it's idempotent, so you
can modify `setup.yml` and rerun playbook as you wish

**NOTE:** it is hard to keep changes in playbook and on remote server in
  sync. Please try to avoid editing remote configs directly, aiming for
  idempotent playbook instead.
