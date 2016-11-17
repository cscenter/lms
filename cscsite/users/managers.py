from __future__ import unicode_literals, absolute_import

from django.contrib.auth.models import UserManager
from django.db.models import Prefetch, Count, query

from learning.models import CourseOfferingTeacher
from learning.settings import GRADES


class CSCUserQuerySet(query.QuerySet):
    # TODO: Refactor later to remove WHERE IN(ids) due to performance reasons,
    # rename ProgressReport.get_queryset after that. Add tests before
    # Investigate how to use tmp table with JOIN in that case?
    def students_info(self,
                      filters=None,
                      exclude=None,
                      exclude_grades=None,
                      semester=False):
        """Returns list of students with all related courses, shad-courses
           practices and projects, etc"""

        from .models import CSCUser, SHADCourseRecord
        from learning.models import Enrollment, CourseClass, Semester, \
            CourseOffering
        from learning.projects.models import ProjectStudent

        # Note: At the same time student must be only in one of these groups
        # So, group_by not necessary for this m2m relationship (in theory)
        filters = filters or {}
        if "groups__in" not in filters:
            filters["groups__in"] = [
                CSCUser.group.STUDENT_CENTER,
                CSCUser.group.GRADUATE_CENTER,
                CSCUser.group.VOLUNTEER
            ]
        q = self.filter(**filters)

        if exclude:
            q = q.exclude(**exclude)

        if exclude_grades is None:
            exclude_grades = [GRADES.unsatisfactory, GRADES.not_graded]
        enrollment_qs = (Enrollment.objects
                         .order_by('course_offering__course__name'))
        shad_qs = SHADCourseRecord.objects.get_queryset()
        if exclude_grades:
            enrollment_qs = enrollment_qs.exclude(grade__in=exclude_grades)
            shad_qs = shad_qs.exclude(grade__in=exclude_grades)

        if isinstance(semester, Semester):
            semester_upper_bound = semester.index
            enrollment_qs = enrollment_qs.filter(
                course_offering__semester__index__lte=semester_upper_bound)
            shad_qs = shad_qs.filter(
                semester__index__lte=semester_upper_bound
            )

        # Note: No idea how it works with thousands students
        # due to user_id IN(blabla thousands ids), but it's ok now.
        return (
            q
            .order_by('last_name', 'first_name')
            .prefetch_related(
                'groups',  # Mb we can do it without user_id IN(blabla million ids)
                Prefetch(
                    'enrollment_set',
                    queryset=enrollment_qs,
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
                    # Note (Zh): Show pure lecturers first (=1),
                    # then teachers with lecturer role (values >1), then others
                    queryset=CSCUser.objects.extra(
                        select={
                            'is_lecturer': '"%s"."roles" & %s' %
                            (CourseOfferingTeacher._meta.db_table,
                             int(CourseOfferingTeacher.roles.lecturer))
                        },
                        order_by=["-is_lecturer",
                                  "%s.roles" % CourseOfferingTeacher._meta.db_table,
                                  "last_name",
                                  "first_name"]
                    )
                ),
                Prefetch(
                    'projectstudent_set',
                    queryset=(ProjectStudent.objects
                              .select_related('project', 'project__semester')
                              .order_by('project__semester__index',
                                        'project__name')),
                    to_attr='projects_through'
                ),
                Prefetch(
                    'study_programs',
                ),
                Prefetch(
                    'shadcourserecord_set',
                    queryset=shad_qs,
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
