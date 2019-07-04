# -*- coding: utf-8 -*-
from datetime import datetime

from django.core.management import BaseCommand
from django.db import transaction

from learning.models import GraduateProfile
from learning.settings import StudentStatuses
from users.models import User


class Command(BaseCommand):
    help = "Create alumni profiles for students who will graduate soon"

    def add_arguments(self, parser):
        parser.add_argument('graduated_on', metavar='GRADUATION_DATE',
                            help='Graduation date in dd.mm.yyyy format')

    def handle(self, *args, **options):
        graduated_on_str = options['graduated_on']
        graduated_on = datetime.strptime(graduated_on_str, "%d.%m.%Y").date()
        will_graduate_list = (User.objects
                              .has_role(User.roles.STUDENT_CENTER,
                                        User.roles.VOLUNTEER)
                              .filter(status=StudentStatuses.WILL_GRADUATE))

        for student in will_graduate_list:
            with transaction.atomic():
                defaults = {
                    "graduated_on": graduated_on,
                    "details": {},
                    "is_active": False
                }
                profile, created = GraduateProfile.objects.get_or_create(
                    student=student,
                    defaults=defaults)
                if not created:
                    profile.save()
