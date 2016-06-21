# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.management import BaseCommand
from django.utils.timezone import now

from learning.settings import STUDENT_STATUS
from users.models import CSCUser


class Command(BaseCommand):
    help = ("Get all students with status `will_graduate` and replace there "
            "student group with `GRADUATE_CENTER`. "
            "Also clean status and set graduation year.")

    def handle(self, *args, **options):
        will_graduate_list = CSCUser.objects.filter(groups__in=[
            CSCUser.group_pks.STUDENT_CENTER,
            CSCUser.group_pks.VOLUNTEER,
        ], status=STUDENT_STATUS.will_graduate)

        for user in will_graduate_list:
            user.groups.remove(CSCUser.group_pks.STUDENT_CENTER)
            user.groups.remove(CSCUser.group_pks.VOLUNTEER)
            user.groups.add(CSCUser.group_pks.GRADUATE_CENTER)
            user.graduation_year = now().year
            user.status = ""
            user.save()
