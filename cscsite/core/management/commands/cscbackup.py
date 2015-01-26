# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from datetime import datetime
from io import BytesIO
import os
import shutil
import socket
import tarfile

from django.core import management
from django.core.management.base import BaseCommand, CommandError

from boto.s3.connection import S3Connection


BACKUP_NAME_TEMPLATE = "{hostname}_{dt_str}/{backup_type}{maybe_tar}.gz"
BACKUP_DT_FORMAT = '%Y-%m-%d-%H%M%S'


def format_backup_name(backup_type, start_at):
    assert backup_type in ['db', 'media']
    args = {'hostname': socket.gethostname(),
            'dt_str': start_at.strftime(BACKUP_DT_FORMAT),
            'backup_type': backup_type,
            'maybe_tar': '' if backup_type == 'db' else '.tar'}
    return BACKUP_NAME_TEMPLATE.format(**args)


def report_to(f, s):
    dt = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
    f.write("{0} {1}".format(dt, s))


def write_file(filehandle, bucket, bucket_path):
    # NOTE(Dmitry): taken from django-dbbackup
    # Use multipart upload because normal upload maximum is 5 GB.
    filehandle.seek(0)
    handle = bucket.initiate_multipart_upload(bucket_path)
    try:
        chunk = 1
        while True:
            chunkdata = filehandle.read(5 * 1024 * 1024)
            if not chunkdata:
                break
            tmpfile = BytesIO(chunkdata)
            tmpfile.seek(0)
            handle.upload_part_from_file(tmpfile, chunk)
            tmpfile.close()
            chunk += 1
        handle.complete_upload()
    except Exception:
        handle.cancel_upload()
        raise


class Command(BaseCommand):
    help = ("Backs everything up to S3, taking into account "
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

        report("backing up db into {} with django-dbbackup"
               .format(backup_dir))
        start_at = datetime.now()
        management.call_command('dbbackup', compress=True)
        backup_files = os.listdir(backup_dir)
        assert ["default.backup"] == backup_files

        # NOTE(Dmitry): backing up media manually because django-dbbackup
        #               forms .tar.gz with *full* pathes
        report("backing up media into {}".format(backup_dir))
        tgz = tarfile.open(name=os.path.join(backup_dir, "media.tar.gz"),
                           mode='w:gz')
        media_root_len = (len(settings.MEDIA_ROOT)
                          if settings.MEDIA_ROOT.endswith("/")
                          else len(settings.MEDIA_ROOT) + 1)
        for root, dirs, files in os.walk(settings.MEDIA_ROOT):
            if len(files) > 0:
                # strip media root
                relative_root = root[media_root_len:]
                for f in files:
                    tgz.add(os.path.join(root, f),
                            arcname=os.path.join(relative_root, f))
        tgz.close()

        report("both backups in place, proceeding to S3 connection")
        conn = S3Connection(
            aws_access_key_id=settings.DBBACKUP_S3_ACCESS_KEY,
            aws_secret_access_key=settings.DBBACKUP_S3_SECRET_KEY,
            host=settings.DBBACKUP_S3_DOMAIN,
            is_secure=True)
        bucket = conn.get_bucket(settings.DBBACKUP_S3_BUCKET)

        report("writing backups to S3")
        for f, backup_type in [("default.backup", 'db'),
                               ("media.tar.gz", 'media')]:
            bucket_fname = format_backup_name(backup_type, start_at)
            # NOTE(Dmitry): it's not os.path because it's S3
            bucket_path = "/".join([settings.DBBACKUP_S3_DIRECTORY,
            bucket_fname])
            local_path = "/".join([backup_dir, f])
            write_file(open(local_path, 'rb'), bucket, bucket_path)
            report('wrote {} to S3://{}'.format(f, bucket_path))

        report("done")
