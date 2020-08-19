from typing import List

from django.conf import settings
from django.contrib.auth.models import UserManager
from django.db.models import Prefetch, query, Q

from learning.settings import GradeTypes


# FIXME: return only queryset for all `get_*_progress` methods
def get_enrollments_progress(lookup='enrollment_set',
                             filters: List[Q] = None,
                             to_attr='enrollments_progress') -> Prefetch:
    from learning.models import Enrollment
    filters = filters or []
    queryset = (Enrollment.active
                .filter(*filters)
                .select_related('course',
                                'course__meta_course',
                                'course__semester')
                .only('pk', 'created', 'student_id', 'course_id',
                      'grade')
                .order_by('course__semester__index'))
    return Prefetch(lookup, queryset=queryset, to_attr=to_attr)


def get_projects_progress(lookup='projectstudent_set',
                          filters: List[Q] = None,
                          to_attr='projects_progress') -> Prefetch:
    from projects.models import ProjectStudent
    filters = filters or []
    queryset = (ProjectStudent.objects
                .filter(*filters)
                .select_related('project', 'project__semester')
                .only('pk', 'project_id', 'student_id',
                      'final_grade', 'project__project_type',
                      'project__name', 'project__is_external',
                      'project__status',
                      'project__semester_id',
                      'project__semester__index',
                      'project__semester__year',
                      'project__semester__type', )
                .order_by('project__semester__index',
                          'project__name')
                .prefetch_related("project__supervisors"))
    return Prefetch(lookup, queryset=queryset, to_attr=to_attr)


def get_shad_courses_progress(lookup='shadcourserecord_set',
                              filters: List[Q] = None,
                              to_attr='shads') -> Prefetch:
    from .models import SHADCourseRecord
    filters = filters or []
    queryset = (SHADCourseRecord.objects
                .filter(*filters))
    return Prefetch(lookup, queryset=queryset, to_attr=to_attr)


class UserQuerySet(query.QuerySet):
    def has_role(self, *roles, site_id=settings.SITE_ID):
        """
        Filter users who have at least one of the provided roles
        for current site. Could return duplicates.
        """
        return self.filter(group__role__in=roles,
                           group__site_id=site_id)

    def student_progress(self, exclude_grades: List[str] = None,
                         until_term: "Semester" = None):
        """
        Prefetch student progress: courses, shad/online courses and projects

        Parameters:
            exclude_grades: Filter out records with provided grade values
            until_term: Get records before this term (inclusive)
        """

        enrollment_filters = []
        if until_term:
            q_ = Q(course__semester__index__lte=until_term.index)
            enrollment_filters.append(q_)
        if exclude_grades:
            q_ = ~Q(grade__in=exclude_grades)
            enrollment_filters.append(q_)

        shad_filters = []
        if exclude_grades:
            shad_filters.append(~Q(grade__in=exclude_grades))
        if until_term:
            shad_filters.append(Q(semester__index__lte=until_term.index))

        return (self.prefetch_related(
            get_enrollments_progress(
                lookup='enrollment_set',
                filters=enrollment_filters
            ),
            get_projects_progress(),
            get_shad_courses_progress(
                lookup='shadcourserecord_set',
                filters=shad_filters
            ),
            Prefetch('onlinecourserecord_set', to_attr='online_courses')))


class CustomUserManager(UserManager.from_queryset(UserQuerySet)):
    use_in_migrations = False
