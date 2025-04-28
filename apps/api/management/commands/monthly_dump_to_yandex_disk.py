import csv
import os
import io
import yadisk
from django.core.management import BaseCommand
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from users.models import StudentStatusLog, StudentTypes
from api.models import ExternalServiceToken


class Command(BaseCommand):
    help = "Monthly dump student status logs to yandex disk"

    def _create_parent_directories(self, client, path):
        """Ensure all parent directories exist on Yandex Disk."""
        parent_path = os.path.dirname(path)
        if not parent_path or client.exists(parent_path):
            return
        self._create_parent_directories(client, parent_path)
        client.mkdir(parent_path)

    def handle(self, *args, **options):
        with io.StringIO() as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow([
                _('User ID'), 
                _('Student Profile ID'), 
                _('Student type'), 
                _('Entry Added'), 
                _('Status'), 
                _('Former status')
            ])
            
            status_logs = StudentStatusLog.objects.filter(
                student_profile__type__in=[StudentTypes.REGULAR, StudentTypes.PARTNER]
            ).select_related('student_profile', 'student_profile__user')
            for log in status_logs:
                student_profile = log.student_profile
                csv_writer.writerow([
                    student_profile.user.id,
                    student_profile.id,
                    student_profile.get_type_display(),
                    log.changed_at,
                    log.get_status_display(),
                    log.get_former_status_display()
                ])
            
            csv_file.seek(0)
            
            client = yadisk.Client(
                token=ExternalServiceToken.objects.get(service_tag="syrop_yandex_disk").access_key,
                default_args={"overwrite": True}
            )
            
            with client:
                if not client.check_token():
                    raise AssertionError("Token seems to be invalid. Is it expired?")
                
                today = timezone.now().date().isoformat()
                target_path = f"/ysda/monthly_student_status_logs/student_status_logs_{today}.csv"
                self._create_parent_directories(client, target_path)
                client.upload(io.BytesIO(csv_file.getvalue().encode()), target_path)
