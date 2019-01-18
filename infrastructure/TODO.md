## Critical:
* Do not delete lambda functions logs on recreation
* restore db and media/ with playbook
* Add `AbortIncompleteMultipartUpload` Lifecycle rule to cscenter backup bucket.
* Think how to update python version without breaking site for updating period (now it does by removing current venv. No idea how to properly rename venv :<)
* Clear, then warm cache (social_crawler, /alumni and so on)
* Separate nginx configurations

## important:
* add `registration` app to cscenter, then remove club worker?
* restore db from s3
* `# Redirect from `www.` to domain without `www` <--- check first that main site domain is two level


## s3 bucket support

No idea in what condition this role. Needs to test.

Create users for buckets with appropriate policy configuration.
If users newly created, save their access keys in `files/backup_user_access_keys.txt` under s3 role directory

TODO:
* Create S3 buckets for backups
* Add lifecycle rule for bucket (30 days TTL for now)
* What about logging for buckets? Crypto?
* Add cost allocation tags for buckets (http://docs.aws.amazon.com/AmazonS3/latest/UG/CostAllocationTagging.html)


# provision

* Add new instance to known_hosts (on local machine)
* mv Elastic IP from old instance to new
* tmux create session https://gist.github.com/henrik/1967800 and save them