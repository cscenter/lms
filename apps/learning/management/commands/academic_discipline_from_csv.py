from django.conf import settings
from django.db.models import Q

from admission.management.commands._utils import CurrentCampaignMixin
import csv
from datetime import datetime
from django.core.management import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from study_programs.models import AcademicDiscipline
from users.models import User, StudentTypes
from users.services import get_student_profile, update_student_academic_discipline


class Command(CurrentCampaignMixin, BaseCommand):
    help = """
    Set academic discipline and create academic discipline log for user with email from csv
    Example: ./manage.py academic_discipline_from_csv --date=2024-09-15
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--filename",
            type=str,
            default='disciplines.csv',
            help="csv file name",
        )
        parser.add_argument(
            "--delimiter",
            type=str,
            default=',',
            help="csv delimiter",
        )
        parser.add_argument(
            "--date",
            type=str,
            default="today",
            help="date of interview in YYYY-MM-DD format",
        )
        parser.add_argument(
            "--year_of_admission",
            type=int,
            default=0,
            help="Year of admission for student profile filter",
        )
        parser.add_argument(
            "--editor_id",
            type=int,
            default=15418,
            help="ID of editor",
        )

    def handle(self, *args, **options):
        delimiter = options["delimiter"]
        filename = options["filename"]
        date = timezone.now().date() if options["date"] == "today" \
            else datetime.strptime(options["date"], '%Y-%m-%d').date()
        year_of_admission = timezone.now().date().year if options["year_of_admission"] == 0 else options["year_of_admission"]
        editor = User.objects.get(pk=options["editor_id"])
        with open(filename) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            headers = next(reader)
            counter = 0
            with transaction.atomic():
                for row in reader:
                    id = int(row["Профиль на сайте"].split('/')[2])
                    try:
                        user = User.objects.get(id=id)
                    except User.DoesNotExist:
                        print(f'{id} does not exists')
                        raise
                    academic_discipline_name = row["Текстовый ответ"]
                    try:
                        academic_discipline = AcademicDiscipline.objects.get(name=academic_discipline_name)
                    except AcademicDiscipline.DoesNotExist:
                        print(f'{academic_discipline_name} does not exists')
                        raise
                    student_profile = get_student_profile(user, site=settings.SITE_ID,
                                                          profile_type=StudentTypes.REGULAR,
                                                          filters=[Q(year_of_admission=year_of_admission)])
                    if student_profile is None:
                        print(f'No regular student profile with {year_of_admission = } and {user = }')
                        continue
                    if student_profile.academic_discipline is not None:
                        print(f'Academic discipline is aleady set for {student_profile}')
                        continue
                    update_student_academic_discipline(student_profile,
                                                       new_academic_discipline=academic_discipline,
                                                       editor=editor,
                                                       changed_at=date)
                    counter += 1
                if input(f'\nБудут заменены {counter} направлений и созданы логи на {date} от лица {editor}\n'
                         f'Введите "y" для подтверждения: ') != "y":
                    raise CommandError("Error asking for approval. Canceled")
