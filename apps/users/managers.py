from typing import List

from django.conf import settings
from django.contrib.auth.models import UserManager
from django.db.models import Prefetch, query

from courses.models import CourseTeacher
from learning.settings import GradeTypes


class UserQuerySet(query.QuerySet):
    def has_role(self, *roles):
        """
        Filter users who have at least one of the provided roles
        for current site. Could return duplicates.
        """
        return self.filter(group__role__in=roles,
                           group__site_id=settings.SITE_ID)

    def student_progress(self, exclude_grades: List[str] = None,
                         before_term: "Semester" = None):
        """
        Prefetch student progress: courses, shad/online courses and projects

        Parameters:
            exclude_grades: Filter out records with provided grade values
            before_term: Get records before this term (inclusive)
        """

        from .models import User, SHADCourseRecord
        from learning.models import Enrollment
        from projects.models import ProjectStudent

        # Note: Show lecturers first, then seminarians, then others
        teachers_qs = User.objects.extra(
            select={
                'is_lecturer': '"%s"."roles" & %s' % (CourseTeacher._meta.db_table, int(CourseTeacher.roles.lecturer)),
                'is_seminarian': '"%s"."roles" & %s' % (CourseTeacher._meta.db_table, int(CourseTeacher.roles.seminar)),
            },
            order_by=["-is_lecturer", "-is_seminarian", "last_name", "first_name"]
        )

        enrollment_qs = (Enrollment.active
                         .select_related("course", "course__meta_course",
                                         "course__semester")
                         .annotate(grade_weight=GradeTypes.to_int_case_expr())
                         .only('pk', 'student_id', 'grade',
                               'course__semester_id',
                               'course__meta_course_id',
                               'course__meta_course__name',
                               'course__meta_course__name_ru',
                               'course__is_open',
                               'course__grading_type',)
                         .prefetch_related(Prefetch("course__teachers",
                                                    queryset=teachers_qs))
                         )
        if before_term:
            enrollment_qs = enrollment_qs.filter(
                course__semester__index__lte=before_term.index)
        if exclude_grades:
            enrollment_qs = enrollment_qs.exclude(grade__in=exclude_grades)

        shad_qs = SHADCourseRecord.objects.get_queryset()
        if exclude_grades:
            shad_qs = shad_qs.exclude(grade__in=exclude_grades)
        if before_term:
            shad_qs = shad_qs.filter(semester__index__lte=before_term.index)

        return (
            self
            .prefetch_related(
                Prefetch('enrollment_set',
                         queryset=enrollment_qs,
                         to_attr="enrollments_progress"),
                Prefetch(
                    'projectstudent_set',
                    queryset=(ProjectStudent.objects
                              .select_related('project', 'project__semester')
                              .only('pk', 'project_id', 'student_id',
                                    'final_grade', 'project__project_type',
                                    'project__name', 'project__is_external',
                                    'project__status',
                                    'project__semester__index',
                                    'project__semester__year',
                                    'project__semester__type',)
                              .order_by('project__semester__index',
                                        'project__name')
                              .prefetch_related("project__supervisors")),
                    to_attr='projects_progress'
                ),
                Prefetch('shadcourserecord_set',
                         queryset=shad_qs,
                         to_attr='shads'),
                Prefetch('onlinecourserecord_set',
                         to_attr='online_courses'),
            )
        )


class CustomUserManager(UserManager.from_queryset(UserQuerySet)):
    use_in_migrations = False
