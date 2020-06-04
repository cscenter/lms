# -*- coding: utf-8 -*-
from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from django.core.management import BaseCommand
from django.db import transaction
from django.utils.timezone import now

from learning.models import GraduateProfile
from learning.settings import StudentStatuses
from users.constants import Roles
from users.models import User, StudentProfile, StudentTypes, StudentStatusLog


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('graduated_on', metavar='GRADUATION_DATE',
                            help='Graduation date in dd.mm.yyyy format')

    def handle(self, *args, **options):
        graduated_on_str = options['graduated_on']
        graduated_on = datetime.strptime(graduated_on_str, "%d.%m.%Y").date()
        will_graduate_list = (StudentProfile.objects
                              .filter(type=StudentTypes.REGULAR,
                                      status=StudentStatuses.WILL_GRADUATE))

        admin = User.objects.get(pk=1)
        for student_profile in will_graduate_list:
            user_account = student_profile.user
            with transaction.atomic():
                user_account.remove_group(Roles.STUDENT)
                user_account.add_group(Roles.GRADUATE)
                # FIXME: use `creat_graduate_profiles` instead
                GraduateProfile.objects.update_or_create(
                    student_profile=student_profile,
                    defaults={
                        "is_active": True,
                        "graduated_on": graduated_on,
                        "details": {}
                    })
                student_profile.status = StudentStatuses.GRADUATE
                student_profile.save()
                # Add new status log entry
                log_entry = StudentStatusLog(status=StudentStatuses.GRADUATE,
                                             student_profile=student_profile,
                                             entry_author=admin)
                log_entry.save()
        cache_key_pattern = GraduateProfile.HISTORY_CACHE_KEY_PATTERN
        cache_key = cache_key_pattern.format(site_id=settings.SITE_ID)
        cache.delete(cache_key)
        # Drop cache on /{YEAR}/ page
        cache.delete("alumni_{}_stats".format(now().year))
