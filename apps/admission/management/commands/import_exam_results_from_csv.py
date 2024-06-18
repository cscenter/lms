import csv
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from admission.models import Applicant, Exam
from ...constants import ApplicantStatuses
from ._utils import CurrentCampaignMixin
from admission.constants import ChallengeStatuses
from decimal import Decimal
from collections import defaultdict


class Command(CurrentCampaignMixin, BaseCommand):
    help = 'Update exam scores from a CSV file'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--filename",
            type=str,
            default='results.csv',
            help="csv file name",
        )
        parser.add_argument(
            "--delimiter",
            type=str,
            default=',',
            help="csv delimiter",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            default=False,
            dest="commit",
            help="Commit changes to database."
        )

    def handle(self, *args, **options):
        delimiter = options["delimiter"]
        filename = options["filename"]
        commit = options["commit"]
        before_exam = [ApplicantStatuses.PERMIT_TO_EXAM,
                       ApplicantStatuses.FAILED_OLYMPIAD,
                       ApplicantStatuses.ACCEPT_PAID]
        campaigns = self.get_current_campaigns(options, confirm=False)

        with open(filename) as csvfile:
            reader = csv.reader(csvfile, delimiter=delimiter)
            headers = next(reader)
            with transaction.atomic():
                total_by_compaign = defaultdict(int)
                for row in reader:
                    yandex_login = row[0]
                    score = Decimal(row[1])

                    try:
                        applicant = Applicant.objects.get(yandex_login=yandex_login, campaign__in=campaigns,
                                                          status__in=before_exam)
                    except Applicant.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f'Applicant with login {yandex_login} does not exist'))
                        continue
                    except Applicant.MultipleObjectsReturned:
                        self.stdout.write(self.style.ERROR(f'There are many applicants with login {yandex_login}'))
                        continue
                    total_by_compaign[applicant.campaign] += 1
                    exam, created = Exam.objects.get_or_create(applicant=applicant,
                                                               defaults={
                                                                   'score': score,
                                                                   'status': ChallengeStatuses.MANUAL
                                                               })
                    if not created:
                        exam.score = score
                        exam.save()

                    if created:
                        self.stdout.write(
                            self.style.SUCCESS(f'Created exam for applicant {yandex_login} with score {score}'))
                for campaign, total in total_by_compaign.items():
                    print(f'{campaign}: {total}')
                if input("Продолжить? [y/n] ") != "y":
                    self.stdout.write("Aborted")
                    return
                if not commit:
                    raise CommandError("Use --commit to apply changes.")
