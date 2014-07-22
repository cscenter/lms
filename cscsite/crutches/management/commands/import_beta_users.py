from __future__ import unicode_literals

import csv
from datetime import date

from django.core.management import BaseCommand, CommandError

from users.models import CSCUser


class Command(BaseCommand):
    """
    To generate the CSV execute the following command:

      $ mysql -B -uroot -p cscenter -e "
      > SELECT * FROM c_auth_userprofile
      > INNER JOIN auth_user ON auth_user.id = c_auth_userprofile.user_id
      > INNER JOIN c_auth_studentprofile
      > ON c_auth_studentprofile.userprofile_ptr_id = c_auth_userprofile.id;" \
      \ > beta.compscicenter.ru.csv
    """

    args = "path/to/dump.csv"
    help = "Imports users from a CSV dump of beta.compsicenter.ru"

    def handle(self, *args, **options):
        try:
            [path] = args
            with open(path, "rU") as f:
                data = list(csv.DictReader(f, dialect=csv.excel_tab))
        except (ValueError, IOError):
            raise CommandError("CSV wher art thou?")

        for row in data:
            if row["is_active"] != "1":
                continue

            current_year = date.today().year
            enrollment_year = graduation_year = None
            if str(row["cs_center_year"]).isdigit():
                enrollment_year = current_year - int(row["cs_center_year"])

            if row["status"] == "graduated":
                graduation_year = current_year  # unsure about this.

            user = CSCUser(first_name=row["first_name"],
                           last_name=row["last_name"],
                           patronymic=row["middle_name"],
                           email=row["email"],
                           username=row["username"],
                           enrollment_year=enrollment_year,
                           graduation_year=graduation_year)
            user.password = row["password"]
            user.save()




