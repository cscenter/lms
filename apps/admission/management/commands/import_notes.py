import csv

from django.db import transaction
from django.core.management import BaseCommand
from admission.models import Applicant

from ._utils import CurrentCampaignMixin
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

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options, confirm=False)
        delimiter = options["delimiter"]
        filename = options["filename"]
        with open(filename) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            prefix = '/admission/applicants/'
            with transaction.atomic():
                for row in reader:
                    note, applicant_url, email = row['Заметки'], row['ID'], row['Email']
                    first_name, last_name, patronymic = row['Имя'], row['Фамилия'], row['Отчество']
                    assert applicant_url.startswith(prefix)
                    assert applicant_url[-1] == '/'
                    applicant_id = int(applicant_url[len(prefix):-1])
                    applicant = Applicant.objects.get(pk=applicant_id)
                    assert(applicant.campaign in campaigns)
                    assert(applicant.first_name == first_name)
                    assert(applicant.last_name == last_name)
                    assert(applicant.patronymic == patronymic)
                    assert(applicant.email == email)
                    applicant.admin_note = note
                    applicant.save()
                    print(f"{last_name} {first_name} {patronymic}, {applicant.campaign}: {note}")
