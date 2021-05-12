# -*- coding: utf-8 -*-

from django.core.management import BaseCommand

from learning.models import Enrollment
from learning.settings import GradeTypes, StudentStatuses
from users.constants import Roles
from users.models import User


class Command(BaseCommand):
    help = """
    Shows list of teachers who participated in learning students with 
    `will_graduate` status.
    """

    def handle(self, *args, **options):
        roles = (Roles.STUDENT, Roles.VOLUNTEER)
        will_graduate_list = (User.objects
                              .has_role(*roles)
                              .filter(status=StudentStatuses.WILL_GRADUATE)
                              .values_list("pk", flat=True))

        # Collect unique courses among all students
        courses = set()
        for student_id in will_graduate_list:
            student_courses = (Enrollment.active
                               .filter(student_id=student_id)
                               .exclude(grade__in=GradeTypes.unsatisfactory_grades)
                               .values_list("course_id", flat=True))
            for co_id in student_courses:
                courses.add(co_id)

        teachers = (User.objects
                    .filter(courseteacher__course_id__in=courses)
                    .only("first_name", "last_name", "patronymic")
                    .distinct())
        for teacher in teachers:
            self.stdout.write(f"{teacher.last_name} {teacher.first_name}")
