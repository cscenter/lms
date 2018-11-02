# -*- coding: utf-8 -*-

from django.core.management import BaseCommand

from learning.models import Enrollment
from learning.settings import GRADES, StudentStatuses
from users.models import User


class Command(BaseCommand):
    help = ("Show distinct teachers among all students "
            "with status `will_graduate`")

    def handle(self, *args, **options):
        student_groups = [User.roles.STUDENT_CENTER, User.roles.VOLUNTEER]
        will_graduate_list = (User.objects
                              .filter(groups__in=student_groups,
                                      status=StudentStatuses.will_graduate)
                              .values_list("pk", flat=True))

        # Collect unique courses among all students
        courses = set()
        for student_id in will_graduate_list:
            student_courses = (Enrollment.active
                               .filter(student_id=student_id)
                               .exclude(grade__in=[GRADES.unsatisfactory,
                                                   GRADES.not_graded])
                               .values_list("course_id", flat=True))
            for co_id in student_courses:
                courses.add(co_id)

        teachers = (User.objects
                    .filter(courseteacher__course_id__in=courses)
                    .only("first_name", "last_name", "patronymic")
                    .distinct())
        for teacher in teachers:
            self.stdout.write(f"{teacher.last_name} {teacher.first_name}")
