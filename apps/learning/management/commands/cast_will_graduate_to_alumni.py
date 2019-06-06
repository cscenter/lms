# -*- coding: utf-8 -*-
from datetime import datetime

from django.core.cache import cache
from django.core.management import BaseCommand
from django.db import transaction
from django.utils.timezone import now

from admission.models import Applicant
from learning.models import GraduateProfile
from learning.settings import StudentStatuses
from users.models import User


class Command(BaseCommand):
    help = ("Get all students with status `will_graduate` and replace there "
            "student group with `GRADUATE_CENTER`. "
            "Also clean status and set graduation year.")

    def add_arguments(self, parser):
        parser.add_argument('graduation_at', metavar='GRADUATION_DATE',
                            help='Graduation date in dd.mm.yyyy format')

    def handle(self, *args, **options):
        graduation_at_str = options['graduation_at']
        graduation_at = datetime.strptime(graduation_at_str, "%d.%m.%Y").date()
        will_graduate_list = User.objects.filter(groups__in=[
            User.roles.STUDENT_CENTER,
            User.roles.VOLUNTEER,
        ], status=StudentStatuses.WILL_GRADUATE)

        for student in will_graduate_list:
            defaults = {
                "graduation_at": graduation_at,
            }
            with transaction.atomic():
                student.groups.remove(User.roles.STUDENT_CENTER)
                student.groups.remove(User.roles.VOLUNTEER)
                student.groups.add(User.roles.GRADUATE_CENTER)
                student.graduation_year = now().year
                student.status = ""
                student.save()
                GraduateProfile.objects.get_or_create(student=student,
                                                      defaults=defaults)

        cache.delete("cscenter_last_graduation_year")
        # Drop cache on /{YEAR}/ page
        cache.delete("alumni_{}_stats".format(now().year))
