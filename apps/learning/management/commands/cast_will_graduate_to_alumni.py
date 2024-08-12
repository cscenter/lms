from datetime import datetime

from django.conf import settings
from django.core.cache import cache
from django.core.management import BaseCommand
from django.db import transaction
from django.utils.timezone import now

from learning.models import GraduateProfile
from learning.settings import StudentStatuses
from users.constants import Roles
from users.models import StudentProfile, StudentTypes, User
from users.services import update_student_status


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('graduated_on', metavar='GRADUATION_DATE',
                            help='Graduation date in dd.mm.yyyy format')

    def handle(self, *args, **options):
        graduated_on_str = options['graduated_on']
        graduated_on = datetime.strptime(graduated_on_str, "%d.%m.%Y").date()
        will_graduate_list = (StudentProfile.objects
                              .filter(type=StudentTypes.REGULAR,
                                      status=StudentStatuses.WILL_GRADUATE,
                                      site_id=settings.SITE_ID))

        admin = User.objects.get(pk=1)
        for student_profile in will_graduate_list:
            user_account = student_profile.user
            with transaction.atomic():
                # TODO: update existing record is no other active student profiles with `Student` permission
                user_account.remove_group(Roles.STUDENT)
                user_account.add_group(Roles.GRADUATE)
                # TODO: reuse `create_graduate_profiles` logic
                GraduateProfile.objects.update_or_create(
                    student_profile=student_profile,
                    defaults={
                        "graduated_on": graduated_on,
                    })
                update_student_status(student_profile, new_status=StudentStatuses.GRADUATE,
                                      editor=admin, changed_at=graduated_on)
        cache_key_pattern = GraduateProfile.HISTORY_CACHE_KEY_PATTERN
        cache_key = cache_key_pattern.format(site_id=settings.SITE_ID)
        cache.delete(cache_key)
        # Drop cache on /{YEAR}/ page
        cache.delete("alumni_{}_stats".format(now().year))
