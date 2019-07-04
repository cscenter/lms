# -*- coding: utf-8 -*-
from datetime import datetime

from django.core.cache import cache
from django.core.management import BaseCommand
from django.db import transaction
from django.utils.timezone import now

from learning.models import GraduateProfile
from learning.settings import StudentStatuses
from users.models import User


class Command(BaseCommand):
    help = ("Get all students with status `will_graduate` and replace there "
            "student group with `GRADUATE_CENTER`. "
            "Also clean status and set graduation year.")

    def add_arguments(self, parser):
        parser.add_argument('graduated_on', metavar='GRADUATION_DATE',
                            help='Graduation date in dd.mm.yyyy format')

    def handle(self, *args, **options):
        graduated_on_str = options['graduated_on']
        graduated_on = datetime.strptime(graduated_on_str, "%d.%m.%Y").date()
        will_graduate_list = (User.objects
                              .has_role(User.roles.STUDENT,
                                        User.roles.VOLUNTEER)
                              .filter(status=StudentStatuses.WILL_GRADUATE))

        for student in will_graduate_list:
            with transaction.atomic():
                student.remove_group(User.roles.STUDENT)
                student.remove_group(User.roles.VOLUNTEER)
                student.add_group(User.roles.GRADUATE_CENTER)
                student.status = ""
                student.save()
                defaults = {
                    "is_active": True,
                    "graduated_on": graduated_on,
                    "details": {}
                }
                profile, created = GraduateProfile.objects.get_or_create(
                    student=student,
                    defaults=defaults)
                if not created:
                    profile.is_active = True
                    profile.save()

        cache.delete("cscenter_last_graduation_year")
        # Drop cache on /{YEAR}/ page
        cache.delete("alumni_{}_stats".format(now().year))
