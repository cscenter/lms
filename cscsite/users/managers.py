from __future__ import unicode_literals, absolute_import

from django.contrib.auth.models import UserManager
from django.db.models import Prefetch, Count, query

from learning.models import CourseOfferingTeacher


class CSCUserQuerySet(query.QuerySet):

    def students_info(self,
                      filter=None,
                      exclude=None,
                      semester=False):
        """Returns list of students with all related courses, shad-courses
           practices and projects, etc"""

        from .models import CSCUser, SHADCourseRecord
        from learning.models import Enrollment, CourseClass, StudentProject, \
            Semester, CourseOffering

        # Note: At the same time student must be in one of these groups
        # So, group_by not neccessary for this m2m relationship (in theory)
        filter = filter or {}
        if not "groups__in" in filter:
            filter["groups__in"] = [
                CSCUser.group_pks.STUDENT_CENTER,
                CSCUser.group_pks.GRADUATE_CENTER,
                CSCUser.group_pks.VOLUNTEER
            ]
        q = self.filter(**filter)

        if exclude:
            q = q.exclude(**exclude)

        exclude_enrollment_grades = ['unsatisfactory']

        current_semester = Semester.get_current()
        if semester != current_semester:
            exclude_enrollment_grades.append('not_graded')

        enrollment_queryset = (Enrollment.objects
            .exclude(grade__in=exclude_enrollment_grades)
            .order_by('course_offering__course__name'))

        shad_queryset = SHADCourseRecord.objects.get_queryset()

        if semester:
            enrollment_queryset = enrollment_queryset.filter(
                course_offering__semester=semester)
            shad_queryset = shad_queryset.filter(
                semester=semester
            )

        return (
            q
            .order_by('last_name', 'first_name')
            .prefetch_related(
                'groups',
                Prefetch(
                    'enrollment_set',
                    queryset=enrollment_queryset,
                    to_attr='enrollments'
                ),
                Prefetch(
                    'enrollments__course_offering',
                    queryset=CourseOffering.objects.select_related(
                        'semester', 'course')
                ),
                Prefetch(
                    'enrollments__course_offering__courseclass_set',
                    queryset=CourseClass.objects.annotate(Count('pk')),
                ),
                Prefetch(
                    'enrollments__course_offering__teachers',
                    # Note (Zh): Can't solve it with standard ORM instruments
                    queryset=CSCUser.objects.extra(select={
                        'is_lector': '1 & %s.roles' % CourseOfferingTeacher._meta.db_table}).order_by(
                        "-is_lector", "last_name"),
                ),
                Prefetch(
                    'studentproject_set',
                    queryset=StudentProject.objects.order_by('project_type')
                                           .select_related('semester'),
                    to_attr='projects'
                ),
                Prefetch(
                    'study_programs',
                ),
                Prefetch(
                    'shadcourserecord_set',
                    queryset=shad_queryset,
                    to_attr='shads'
                ),
                Prefetch(
                    'onlinecourserecord_set',
                    to_attr='online_courses'
                ),
            )
        )


class CustomUserManager(UserManager.from_queryset(CSCUserQuerySet)):
    use_in_migrations = False
