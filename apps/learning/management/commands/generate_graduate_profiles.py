# -*- coding: utf-8 -*-
from datetime import datetime

from django.core.management import BaseCommand
from django.db import transaction

from learning.models import GraduateProfile
from learning.settings import StudentStatuses
from users.models import User


class Command(BaseCommand):
    help = "Generates graduate profiles for students with WILL_GRADUATE status"

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
            with transaction.atomic():
                defaults = {
                    "graduation_at": graduation_at,
                    "testimonial": student.csc_review,
                    "details": {},
                    "is_active": False
                }
                profile, created = GraduateProfile.objects.get_or_create(
                    student=student,
                    defaults=defaults)
                if not created:
                    profile.testimonial = student.csc_review
                    profile.save()
