from __future__ import unicode_literals

import csv
from datetime import date

from django.core.management import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime
from django.utils.encoding import force_text

from users.models import CSCUser


class Command(BaseCommand):
    """
    To generate the CSV execute the following command:

      $ mysql -B -uroot -p cscenter -e "
      > SELECT username, password, email, is_active, date_joined,
      >        c_auth_userprofile.*, c_auth_studentprofile.*
      > FROM c_auth_userprofile
      > INNER JOIN auth_user ON auth_user.id = c_auth_userprofile.user_id
      > INNER JOIN c_auth_studentprofile
      > ON c_auth_studentprofile.userprofile_ptr_id = c_auth_userprofile.id;" \
      \ > beta.compscicenter.ru.csv
    """

    args = "path/to/dump.csv"
    help = "Imports users from a CSV dump of beta.compscicenter.ru"

    def handle(self, *args, **options):
        try:
            [path] = args
            with open(path, "rU") as f:
                data = list(csv.DictReader(f, dialect=csv.excel_tab))
        except (ValueError, IOError):
            raise CommandError("CSV wher art thou?")

        for row in data:
            if row["is_active"] != "1" or not row["email"]:
                continue

            username, domain = row["email"].split("@")
            if username == "admin":
                # Don't import any extra admins by accident ;)
                username = "{first_name}.{last_name}".format(**row).lower()

            if CSCUser.objects.filter(username=username).exists():
                # Interestingly, some people have registered twice.
                continue

            user = CSCUser.objects.create(
                username=username, password=row["password"],
                email=row["email"],
                first_name=force_text(row["first_name"]),
                last_name=force_text(row["last_name"]),
                patronymic=force_text(row["middle_name"]),
                date_joined=parse_datetime(row["date_joined"]))

            current_year = date.today().year
            if str(row["cs_center_year"]).isdigit():
                user.enrollment_year = \
                    current_year - int(row["cs_center_year"])

            if row["status"] == "graduated":
                user.graduation_year = current_year  # unsure about this.

            user.save()
            user.groups.add(CSCUser.IS_STUDENT_PK)
            if user.graduation_year is not None:
                user.groups.add(CSCUser.IS_GRADUATE_PK)




