# -*- coding: utf-8 -*-
from datetime import datetime

from django.core.cache import cache
from django.core.management import BaseCommand
from django.db import transaction
from django.utils.timezone import now

from learning.models import GraduateProfile
from learning.settings import StudentStatuses
from users.constants import Roles
from users.models import User, StudentProfile, StudentTypes


class Command(BaseCommand):
    help = ("Get all students with status `will_graduate` and replace there "
            "student group with `GRADUATE`. "
            "Also clean status and set graduation year.")

    def add_arguments(self, parser):
        parser.add_argument('graduated_on', metavar='GRADUATION_DATE',
                            help='Graduation date in dd.mm.yyyy format')

    def handle(self, *args, **options):
        graduated_on_str = options['graduated_on']
        graduated_on = datetime.strptime(graduated_on_str, "%d.%m.%Y").date()
        will_graduate_list = (StudentProfile.objects
                              .filter(type=StudentTypes.REGULAR,
                                      status=StudentStatuses.WILL_GRADUATE))

        for student_profile in will_graduate_list:
            user_account = student_profile.user
            with transaction.atomic():
                user_account.remove_group(Roles.STUDENT)
                user_account.remove_group(Roles.VOLUNTEER)
                user_account.add_group(Roles.GRADUATE)
                defaults = {
                    "status": "",
                    "is_active": True,
                    "graduated_on": graduated_on,
                    "details": {}
                }
                profile, created = GraduateProfile.objects.get_or_create(
                    student=user_account,
                    defaults=defaults)
                if not created:
                    profile.is_active = True
                    profile.save()

        cache.delete("csc_graduation_history")
        # Drop cache on /{YEAR}/ page
        cache.delete("alumni_{}_stats".format(now().year))
