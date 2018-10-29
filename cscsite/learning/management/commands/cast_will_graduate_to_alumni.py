# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.cache import cache
from django.core.management import BaseCommand
from django.utils.timezone import now

from learning.settings import STUDENT_STATUS
from users.models import User


class Command(BaseCommand):
    help = ("Get all students with status `will_graduate` and replace there "
            "student group with `GRADUATE_CENTER`. "
            "Also clean status and set graduation year.")

    def handle(self, *args, **options):
        will_graduate_list = User.objects.filter(groups__in=[
            User.group.STUDENT_CENTER,
            User.group.VOLUNTEER,
        ], status=STUDENT_STATUS.will_graduate)

        for user in will_graduate_list:
            user.groups.remove(User.group.STUDENT_CENTER)
            user.groups.remove(User.group.VOLUNTEER)
            user.groups.add(User.group.GRADUATE_CENTER)
            user.graduation_year = now().year
            user.status = ""
            user.save()

        cache.delete("cscenter_last_graduation_year")
        # Drop cache on /{YEAR}/ page
        cache.delete("alumni_{}_stats".format(now().year))
