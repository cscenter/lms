import csv
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from core.models import Branch
from study_programs.models import AcademicDiscipline
from users.constants import GenderTypes
from users.models import PartnerTag, User, StudentTypes, StudentProfile, StudentAcademicDisciplineLog
from users.services import create_account, generate_username_from_email, create_student_profile


class Command(BaseCommand):
    """
    Make partner student profile, account (if needed) and StudentAcademicDisciplineLog from csv

    Example:
        ./manage.py create_partner_profiles --branch=msk --partner=mfti --filename=mfti_students.csv --entry_author_id=16376 --changed_at=01.09.2024 --trust_csv
    """

    help = """Make partner student profiles from csv"""

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--branch",
            type=str,
            help="Branch code to fill it in profile"
        )
        parser.add_argument(
            "--partner",
            type=str,
            help="Partner slug to fill it in profile"
        )
        parser.add_argument(
            "--filename",
            type=str,
            help="Csv file name",
        )
        parser.add_argument(
            "--delimiter",
            type=str,
            default=',',
            help="Csv delimiter",
        )
        parser.add_argument(
            "--entry_author_id",
            type=str,
            help="Id of entry author for StudentAcademicDisciplineLog",
        )
        parser.add_argument(
            "--changed_at",
            type=str,
            help="Date when StudentAcademicDisciplineLog changed_at",
        )
        parser.add_argument(
            "--trust_csv",
            action="store_true",
            default=False,
            help="Apply all changes of mismatched fields automatically",
        )

    def get_branch(self, options) -> Branch:
        branch_code = options["branch"]
        if not branch_code:
            available = Branch.objects.filter(branch__site_id=settings.SITE_ID).values_list("code", flat=True)
            msg = f"Provide the code of the branch. Options: {available}"
            raise CommandError(msg)
        branch = Branch.objects.get(code=branch_code)
        if input(f"Selected branch: {branch}. Is it right?\n"
                 f"y/[n]: ") != "y":
            raise CommandError("Error asking for approval. Canceled")
        return branch

    def get_partner(self, options) -> PartnerTag:
        partner_slug = options["partner"]
        if not partner_slug:
            available = PartnerTag.objects.all().values_list("slug", flat=True)
            msg = f"Provide the slug of the partner. Options: {available}"
            raise CommandError(msg)
        partner = PartnerTag.objects.get(slug=partner_slug)
        if input(f"Selected partner: {partner}. Is it right?\n"
                 f"y/[n]: ") != "y":
            raise CommandError("Error asking for approval. Canceled")
        return partner

    def get_entry_author(self, options) -> User:
        entry_author_id = options["entry_author_id"]
        entry_author = User.objects.get(id=entry_author_id)
        if input(f"Selected entry_author: {entry_author}. Is it right?\n"
                 f"y/[n]: ") != "y":
            raise CommandError("Error asking for approval. Canceled")
        return entry_author

    def get_gender_type(self, gender_str: str) -> str:
        if gender_str == "Мужской":
            return GenderTypes.MALE
        elif gender_str == "Женский":
            return GenderTypes.FEMALE
        elif gender_str == "Другой":
            return GenderTypes.OTHER
        else:
            assert not "possible"

    def handle(self, *args, **options):
        branch = self.get_branch(options)
        partner = self.get_partner(options)
        entry_author = self.get_entry_author(options)
        delimiter = options["delimiter"]
        filename = options["filename"]
        trust_csv = options["trust_csv"]
        changed_at = datetime.strptime(options["changed_at"], "%d.%m.%Y")
        with open(filename) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=delimiter)
            headers = next(reader)
            found_counter = 0
            created_counter = 0
            with transaction.atomic():
                for row in reader:
                    last_name, first_name, patronymic = row["Фамилия"], row["Имя"], row["Отчество"]
                    gender = self.get_gender_type(row["Пол"])
                    gave_permission_at = None if not row["Дата подтверждения согласий (дата и время)"] \
                        else datetime.strptime(row["Дата подтверждения согласий (дата и время)"], "%d.%m.%Y %H:%M:%S")
                    birth_date = datetime.strptime(row["Дата рождения"], "%d.%m.%Y").date()
                    phone, telegram_username, email = row["Номер телефона"], row["ТГ"].replace("@", ""), row["Почта"]
                    academic_discipline = AcademicDiscipline.objects.get(name=row["Направление"])
                    try:
                        user = User.objects.get(email__iexact=email)
                        mismatched_fields = {
                            'gender': (user.gender, gender),
                            'birth_date': (user.birth_date, birth_date),
                            'phone': (user.phone, phone),
                            'telegram_username': (user.telegram_username, telegram_username),
                        }
                        mismatches = {field: (current, expected)
                                      for field, (current, expected) in mismatched_fields.items()
                                      if current != expected}
                        for field, (current, expected) in mismatches.items():
                            if trust_csv:
                                print(f"Changed field '{field}' of user '{user}' from '{current}' to '{expected}'")
                                setattr(user, field, expected)
                                user.save()
                            elif input(f"Change field '{field}' of user '{user}' from '{current}' to '{expected}'?\n"
                                     f"y/[n]: ") == "y":
                                setattr(user, field, expected)
                                user.save()
                        found_counter += 1
                    except User.DoesNotExist:
                        if not gave_permission_at:
                            try:
                                user = User.objects.get(last_name=last_name, first_name=first_name)
                                print(f"STUDENT {last_name} {first_name} {patronymic} HAS ACCOUNT WITH EMAIL '"
                                      f"{user.email}', but '{email}' was provided")
                            except User.DoesNotExist:
                                print(f"NO PERMISSION FOR NEW STUDENT: {last_name} {first_name} {patronymic}")
                        user = create_account(username=generate_username_from_email(email),
                                              password=User.objects.make_random_password(),
                                              email=email,
                                              gender=gender,
                                              time_zone=branch.time_zone,
                                              is_active=True,
                                              first_name=first_name,
                                              last_name=last_name,
                                              patronymic=patronymic,
                                              birth_date=birth_date,
                                              telegram_username = telegram_username)
                        user.phone = phone
                        user.gave_permission_at = gave_permission_at
                        user.save()
                        created_counter += 1

                    profile_fields = {
                        "profile_type": StudentTypes.PARTNER,
                        "year_of_curriculum": timezone.now().year,
                        "user": user,
                        "branch": branch,
                        "year_of_admission": timezone.now().year,
                        "partner": partner
                    }
                    assert not StudentProfile.objects.filter(
                        user=user,
                        branch=branch,
                        type=StudentTypes.PARTNER,
                        partner=partner).exists()
                    student_profile = create_student_profile(**profile_fields)
                    student_profile.academic_disciplines.add(academic_discipline)
                    student_profile.save()

                    log_entry = StudentAcademicDisciplineLog(academic_discipline=academic_discipline,
                                                             student_profile=student_profile,
                                                             entry_author=entry_author,
                                                             changed_at=changed_at)
                    log_entry.save()

                print(f"Found students: {found_counter}")
                print(f"Created students: {created_counter}")
                if input(f"Is everything ok?\n"
                         f"y/[n]: ") != "y":
                    raise CommandError("Error asking for approval. Canceled")
