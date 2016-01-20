from __future__ import unicode_literals, absolute_import

from django.contrib.auth.models import UserManager
from django.db.models import Prefetch, Count, query

from learning.models import CourseOfferingTeacher


class CSCUserQuerySet(query.QuerySet):

    def students_info(self,
                      only_will_graduate=False,
                      enrollments_current_semester_only=False):
        """Returns list of students with all related courses, shad-courses
           practices and projects, etc"""

        from .models import CSCUser
        from learning.models import Enrollment, CourseClass, StudentProject, \
            Semester, CourseOffering

        # Note: At the same time student must be in one of these groups
        # So, group_by not neccessary for this m2m relationship (in theory)
        q = self.filter(
                groups__in=[CSCUser.group_pks.STUDENT_CENTER,
                            CSCUser.group_pks.GRADUATE_CENTER,
                            CSCUser.group_pks.VOLUNTEER]
            )

        if only_will_graduate:
            q = q.filter(status=CSCUser.STATUS.will_graduate)

        exclude_enrollments = ['unsatisfactory']
        if not enrollments_current_semester_only:
            exclude_enrollments.append('not_graded')

        enrollment_queryset = (Enrollment.objects
            .exclude(grade__in=exclude_enrollments)

            .order_by('course_offering__course__name'))

        if enrollments_current_semester_only:
            current_semester = Semester.get_current()
            enrollment_queryset = enrollment_queryset.filter(
                course_offering__semester=current_semester)

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
