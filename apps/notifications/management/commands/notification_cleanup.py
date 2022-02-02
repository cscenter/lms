from datetime import datetime

import pytz

from django.core.management.base import BaseCommand

from courses.constants import SemesterTypes
from courses.models import Semester
from courses.utils import TermPair
from learning.models import AssignmentNotification, CourseNewsNotification


def report(s):
    print("{0} {1}".format(datetime.now().strftime("%Y.%m.%d %H:%M:%S"), s))


class Command(BaseCommand):
    help = "Removes read notifications from previous academic years"

    def handle(self, *args, **options):
        current_semester = Semester.get_current()
        academic_year_start = TermPair(year=current_semester.academic_year,
                                       type=SemesterTypes.AUTUMN)
        starts_at = academic_year_start.starts_at(pytz.UTC)
        objects = (AssignmentNotification.objects
                   .filter(is_unread=False,
                           created__lt=starts_at))
        deleted, _ = objects.delete()
        report(f"{deleted} AssignmentNotifications older than {starts_at} were deleted")
        objects = (CourseNewsNotification.objects
                   .filter(is_unread=False,
                           created__lt=starts_at))
        deleted, _ = objects.delete()
        report(f"{deleted} CourseNewsNotifications older than {starts_at} were deleted")
