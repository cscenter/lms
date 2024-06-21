import csv

from django.db import transaction
from django.core.management import BaseCommand
from admission.models import Applicant

from ._utils import CurrentCampaignMixin
from ...constants import ApplicantInterviewFormats


class Command(CurrentCampaignMixin, BaseCommand):
    help = """Import applicant notes from csv"""

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--filename",
            type=str,
            default='notes.csv',
            help="csv file name",
        )
        parser.add_argument(
            "--delimiter",
            type=str,
            default=',',
            help="csv delimiter",
        )

    def get_interview_format(self, format: str) -> ApplicantInterviewFormats:
        return {
            "очно": ApplicantInterviewFormats.OFFLINE,
            "онлайн": ApplicantInterviewFormats.ONLINE,
            "любой": ApplicantInterviewFormats.ANY
        }[format]

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options, confirm=False)
        delimiter = options["delimiter"]
        filename = options["filename"]
        with open(filename) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            with transaction.atomic():
                for row in reader:
                    note, email, format = row['Заметки'], row['Email'], row['Формат']
                    first_name, last_name, patronymic = row['Имя'], row['Фамилия'], row['Отчество']
                    try:
                        applicant = Applicant.objects.get(campaign__in=campaigns, email=email)
                    except Applicant.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f'Applicant with email {email} does not exist'))
                        continue
                    except Applicant.MultipleObjectsReturned:
                        self.stdout.write(self.style.ERROR(f'There are many applicants with email {email}'))
                        continue

                    if (applicant.first_name != first_name.replace(' ','') or
                        applicant.last_name != last_name.replace(' ','') or
                        applicant.patronymic != patronymic.replace(' ','')):
                        self.stdout.write(self.style.WARNING(f"{applicant.last_name}:{last_name.replace(' ','')}"))
                        self.stdout.write(self.style.WARNING(f"{applicant.first_name}:{first_name.replace(' ','')}"))
                        self.stdout.write(self.style.WARNING(f"{applicant.patronymic}:{patronymic.replace(' ','')}"))
                    applicant.admin_note = note
                    applicant.interview_format = self.get_interview_format(format)
                    applicant.save()
