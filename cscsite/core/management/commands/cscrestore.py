# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from datetime import datetime
from io import BytesIO
from itertools import dropwhile
import os
import shutil
import sys
import tarfile

from django.core import management
from django.core.management.base import BaseCommand, CommandError

from boto.s3.connection import S3Connection


# NOTE(Dmitry): somewhat fragile, works for now
S3_LAST_MODIFIED_FORMAT = "%Y-%m-%dT%H:%M:%S.000Z"


def report_to(f, s):
    dt = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
    f.write("{0} {1}".format(dt, s))


class Command(BaseCommand):
    help = ("Loads latest backup from S3, taking into account "
            "django-dbbackup problems. WARNING: can broke badly "
            "if django-dbbackup is updated")
    can_import_settings = True

    def handle(self, *args, **options):
        from django.conf import settings

        report = lambda x: report_to(self.stdout, x)
        backup_dir = settings.CSC_TMP_BACKUP_DIR

        report("ensuring that {} is an empty dir".format(backup_dir))
        if os.path.isdir(backup_dir):
            shutil.rmtree(backup_dir)
        os.makedirs(backup_dir)

        report("connecting to S3")
        conn = S3Connection(
            aws_access_key_id=settings.DBBACKUP_S3_ACCESS_KEY,
            aws_secret_access_key=settings.DBBACKUP_S3_SECRET_KEY,
            host=settings.DBBACKUP_S3_DOMAIN,
            is_secure=True)
        bucket = conn.get_bucket(settings.DBBACKUP_S3_BUCKET)
        path_dt_pairs = [(key.name, datetime.strptime(key.last_modified,
                                                      S3_LAST_MODIFIED_FORMAT))
                         for key
                         in bucket.list(prefix=settings.DBBACKUP_S3_DIRECTORY)]
        last_modified_path = sorted(path_dt_pairs, key=lambda x: x[1])[-1][0]
        last_modified_dir = "/".join(last_modified_path.split("/")[:-1]) + "/"

        report("fetching backup files from S3://{}".format(last_modified_dir))
        backup_keys = list(bucket.list(prefix=last_modified_dir))
        assert len(backup_keys) == 2
        for key in backup_keys:
            fname = key.name.split("/")[-1]
            assert fname in ['db.gz', 'media.tar.gz']
            fpath = os.path.join(backup_dir, fname)
            key.get_contents_to_filename(fpath)
            report("{} downloaded to {}".format(key.name, fpath))

        report("using django-dbbackup to restore database")
        # NOTE(Dmitry): awkward hack around django-dbbackup's uncoditional
        #               input
        sys_stdin = sys.stdin
        sys.stdin = BytesIO(b'y')
        # management.call_command('dbrestore', uncompress=True,
        #                         filepath=os.path.join(backup_dir, 'db.gz'))
        sys.stdin = sys_stdin

        report("manually restoring media")
        # NOTE(Dmitry): assuming it's OK to overwrite MEDIA_ROOT dir without
        #               deleting files first
        tgz = tarfile.open(name=os.path.join(backup_dir, 'media.tar.gz'),
                           mode='r:gz')
        tgz.extractall(path=settings.MEDIA_ROOT)

        report("done")
