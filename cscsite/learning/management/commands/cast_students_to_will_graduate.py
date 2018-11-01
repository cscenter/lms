# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.management import BaseCommand
from django.db.models import Count, Prefetch, Value, When, Q, F, Case
from django.utils.timezone import now

from learning.models import Enrollment, Semester, OnlineCourse, StudyProgram
from learning.settings import STUDENT_STATUS
from users.models import User, SHADCourseRecord, OnlineCourseRecord


class Command(BaseCommand):
    help = """
Try to set `will_graduate` status and appropriate study programs for 
students who satisfy the requirements.

Requirements:
    * `curriculum_year` >= `current year` - 3
    * >= 3 practices (passed + without grade in current term)
    * passed courses >= 12 (Each club course with < 6 classes count as 0.5)
      We are pretty optimistic in assessment here and think that student 
      will pass all courses they enrolled in current term.
"""

    def handle(self, *args, **options):
        current_term = Semester.get_current()
        # TODO: Restrict programmes by last 4-5 years?
        study_programmes = [sp for sp in StudyProgram.objects.syllabus()]
        students = (User.objects
                    .only("pk", "curriculum_year", "city")
                    # FIXME: move this annotation to manager?
                    .annotate(passed_projects=Count(Case(
                                When(Q(projectstudent__final_grade=Enrollment.GRADES.not_graded) & ~Q(projectstudent__project__semester_id=current_term.pk),
                                     then=Value(None)),
                                When(Q(projectstudent__final_grade=Enrollment.GRADES.unsatisfactory),
                                     then=Value(None)),
                                default=F("projectstudent__pk")
                            ), distinct=True))
                    .filter(groups__in=[User.group.STUDENT_CENTER],
                            curriculum_year__gte=str(current_term.year - 3),
                            passed_projects__gte=3)
                    .exclude(status__in=[User.STATUS.will_graduate,
                                         User.STATUS.expelled])
                    .prefetch_related(
                        Prefetch('onlinecourserecord_set',
                                 queryset=(OnlineCourseRecord.objects
                                           .only("pk", "student_id"))),
                        Prefetch('shadcourserecord_set',
                                 queryset=(SHADCourseRecord.objects
                                           .only("pk",
                                                 "grade",
                                                 "semester_id",
                                                 "student_id")
                                           .order_by())),
                        Prefetch(
                            'enrollment_set',
                            queryset=(Enrollment.active
                                      .select_related("course",
                                                      "course__meta_course",
                                                      "course__semester")
                                      .annotate(classes_total=Count('course__courseclass'))
                                      .order_by()),
                        ))
                    .order_by())

        for student in students.all():
            stats = student.stats(current_term=current_term)
            total_adjusted = (stats["in_term"]["in_progress"] +
                              stats["passed"]["adjusted"])
            if total_adjusted >= 12:
                areas = []
                for program in study_programmes:
                    if (program.year != student.curriculum_year or
                            program.city_id != student.city_id):
                        continue
                    # Student should have at least 1 passed course in each group
                    groups_total = len(program.course_groups.all())
                    groups_satisfied = 0
                    for course_groups in program.course_groups.all():
                        center_courses = stats["passed"]["center_courses"]
                        courses = center_courses.union(
                            stats["in_term"]["courses"])
                        groups_satisfied += any(c.id in courses for c in
                                                 course_groups.courses.all())
                    if groups_total and groups_satisfied == groups_total:
                        areas.append(program.area.code)
                if areas:
                    User.objects.filter(pk=student.pk).update(
                        status=User.STATUS.will_graduate)
                    student.areas_of_study.set(areas)
