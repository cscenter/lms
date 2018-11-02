# -*- coding: utf-8 -*-

from django.core.cache import cache
from django.core.management import BaseCommand
from django.utils.timezone import now

from learning.settings import StudentStatuses
from users.models import User


class Command(BaseCommand):
    help = ("Get all students with status `will_graduate` and replace there "
            "student group with `GRADUATE_CENTER`. "
            "Also clean status and set graduation year.")

    def handle(self, *args, **options):
        will_graduate_list = User.objects.filter(groups__in=[
            User.roles.STUDENT_CENTER,
            User.roles.VOLUNTEER,
        ], status=StudentStatuses.will_graduate)

        for user in will_graduate_list:
            user.groups.remove(User.roles.STUDENT_CENTER)
            user.groups.remove(User.roles.VOLUNTEER)
            user.groups.add(User.roles.GRADUATE_CENTER)
            user.graduation_year = now().year
            user.status = ""
            user.save()

        cache.delete("cscenter_last_graduation_year")
        # Drop cache on /{YEAR}/ page
        cache.delete("alumni_{}_stats".format(now().year))
