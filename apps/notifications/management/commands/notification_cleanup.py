from datetime import datetime

import pytz

from django.core.management.base import BaseCommand

from courses.constants import SemesterTypes
from courses.models import Semester
from courses.utils import TermPair
from learning.models import AssignmentNotification, CourseNewsNotification


class Command(BaseCommand):
    help = "Removes stale notifications"

    def handle(self, *args, **options):
        current_semester = Semester.get_current()
        # Prevents deleting notifications from the spring term
        # if we are at the beginning of the academic year
        if current_semester.type == SemesterTypes.AUTUMN:
            past_semester = TermPair(year=current_semester.academic_year,
                                     type=SemesterTypes.SPRING)
        else:
            past_semester = TermPair(year=current_semester.academic_year,
                                     type=SemesterTypes.AUTUMN)
        starts_at = past_semester.starts_at(pytz.UTC)
        objects = (AssignmentNotification.objects
                   .filter(is_unread=False,
                           created__lt=starts_at))
        deleted, _ = objects.delete()
        self.report(f"{deleted} AssignmentNotifications older than {starts_at} were deleted")
        objects = (CourseNewsNotification.objects
                   .filter(is_unread=False,
                           created__lt=starts_at))
        deleted, _ = objects.delete()
        self.report(f"{deleted} CourseNewsNotifications older than {starts_at} were deleted")

    def report(self, s):
        self.stdout.write("{0} {1}".format(datetime.now().strftime("%Y.%m.%d %H:%M:%S"), s))
