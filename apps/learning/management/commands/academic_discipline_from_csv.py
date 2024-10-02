from django.conf import settings

from admission.management.commands._utils import CurrentCampaignMixin
import csv
from datetime import datetime
from django.core.management import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from study_programs.models import AcademicDiscipline
from users.models import User
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
        editor = User.objects.get(pk=options["editor_id"])
        with open(filename) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            headers = next(reader)
            with transaction.atomic():
                for student_number, row in enumerate(reader):
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
                    student_profile = get_student_profile(user, site=settings.SITE_ID)
                    assert student_profile is not None, user
                    update_student_academic_discipline(student_profile,
                                                       new_academic_discipline=academic_discipline,
                                                       editor=editor,
                                                       changed_at=date)
                if input(f'\nБудут заменены {student_number} направлений и созданы логи на {date} от лица {editor}\n'
                         f'Введите "y" для подтверждения: ') != "y":
                    raise CommandError("Error asking for approval. Canceled")
