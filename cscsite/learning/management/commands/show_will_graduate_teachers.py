# -*- coding: utf-8 -*-

from django.core.management import BaseCommand

from learning.models import Enrollment
from learning.settings import STUDENT_STATUS, GRADES
from users.models import CSCUser


class Command(BaseCommand):
    help = ("Show distinct teachers among all students "
            "with status `will_graduate`")

    def handle(self, *args, **options):
        student_groups = [CSCUser.group.STUDENT_CENTER, CSCUser.group.VOLUNTEER]
        will_graduate_list = (CSCUser.objects
                              .filter(groups__in=student_groups,
                                      status=STUDENT_STATUS.will_graduate)
                              .values_list("pk", flat=True))

        # Collect course offering ids among all students
        co_ids = set()
        for student_id in will_graduate_list:
            student_courses = (Enrollment.active
                               .filter(student_id=student_id)
                               .exclude(grade__in=[GRADES.unsatisfactory,
                                                   GRADES.not_graded])
                               .values_list("course_offering_id", flat=True))
            for co_id in student_courses:
                co_ids.add(co_id)

        teachers = (CSCUser.objects
                    .filter(courseofferingteacher__course_offering_id__in=co_ids)
                    .only("first_name", "last_name", "patronymic")
                    .distinct())
        for teacher in teachers:
            self.stdout.write(f"{teacher.last_name} {teacher.first_name}")
