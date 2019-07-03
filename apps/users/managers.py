from django.contrib.auth.models import UserManager
from django.db.models import Prefetch, query, Q

from courses.models import CourseTeacher


class UserQuerySet(query.QuerySet):
    # TODO: Refactor later to remove WHERE IN(ids) due to performance reasons,
    # rename ProgressReport.get_queryset after that. Add tests before
    # Investigate how to use tmp table with JOIN in that case?
    def students_info(self,
                      filters=None,
                      exclude=None,
                      exclude_grades=None,
                      semester=None):
        """Returns list of students with all related courses, shad-courses
           practices and projects, etc"""

        from .models import User, SHADCourseRecord
        from learning.models import Enrollment
        from courses.models import Semester
        from courses.models import Course
        from learning.projects.models import ProjectStudent

        # Note: At the same time student must be only in one of these groups
        # So, group_by not necessary for this m2m relationship (in theory)
        filters = filters or {}
        if isinstance(filters, dict):
            if "groups__in" not in filters:
                filters["groups__in"] = [
                    User.roles.STUDENT_CENTER,
                    User.roles.GRADUATE_CENTER,
                    User.roles.VOLUNTEER
                ]
            q = self.filter(**filters)
            if exclude:
                q = q.exclude(**exclude)
        elif isinstance(filters, Q):
            q = self.filter(filters)
        else:
            raise TypeError("students_info: unsupported filters type")

        enrollment_qs = (Enrollment.active
                         .order_by('course__meta_course__name'))
        shad_qs = SHADCourseRecord.objects.get_queryset()
        if exclude_grades:
            enrollment_qs = enrollment_qs.exclude(grade__in=exclude_grades)
            shad_qs = shad_qs.exclude(grade__in=exclude_grades)

        if isinstance(semester, Semester):
            semester_upper_bound = semester.index
            enrollment_qs = enrollment_qs.filter(
                course__semester__index__lte=semester_upper_bound)
            shad_qs = shad_qs.filter(
                semester__index__lte=semester_upper_bound
            )

        # Note: No idea how it works with thousands students
        # due to user_id IN(blabla thousands ids), but it's ok now.
        return (
            q
            .select_related('graduate_profile')
            .order_by('last_name', 'first_name')
            .prefetch_related(
                'groups',
                Prefetch(
                    'enrollment_set',
                    queryset=enrollment_qs,
                    to_attr='enrollments'
                ),
                Prefetch(
                    'enrollments__course',
                    queryset=Course.objects.select_related(
                        'semester', 'meta_course')
                ),
                Prefetch(
                    'enrollments__course__teachers',
                    # Note (Zh): Show lecturers first, then seminarians,
                    # then others
                    queryset=User.objects.extra(
                        select={
                            'is_lecturer': '"%s"."roles" & %s' % (CourseTeacher._meta.db_table, int(CourseTeacher.roles.lecturer)),
                            'is_seminarian': '"%s"."roles" & %s' % (CourseTeacher._meta.db_table, int(CourseTeacher.roles.seminar)),
                        },
                        order_by=["-is_lecturer",
                                  "-is_seminarian",
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
                    'graduate_profile__academic_disciplines',
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
            .distinct()
        )


class CustomUserManager(UserManager.from_queryset(UserQuerySet)):
    use_in_migrations = False
