from typing import List, Optional

from django.db.models import Q

from courses.managers import CourseTeacherQuerySet
from courses.models import Course, CourseTeacher


def get_teachers(*, role_priority: Optional[bool] = False,
                 filters: Optional[List[Q]] = None) -> CourseTeacherQuerySet:
    """
    Returns course teachers queryset. Use `role_priority=True` to annotate
    objects with the most priority role within the course.
    """
    filters = filters or []
    qs = (CourseTeacher.objects
          .filter(*filters)
          .select_related('teacher'))
    if role_priority:
        most_priority_role = CourseTeacher.get_most_priority_role_expr()
        qs = qs.annotate(most_priority_role=most_priority_role)
    return qs


def get_lecturers() -> CourseTeacherQuerySet:
    filters = [Q(roles=CourseTeacher.roles.lecturer)]
    return get_teachers(role_priority=False, filters=filters)


def get_reviewers() -> CourseTeacherQuerySet:
    filters = [Q(roles=CourseTeacher.roles.reviewer)]
    return get_teachers(role_priority=False, filters=filters)


def get_course_teachers(*, course: Course,
                        role_priority: Optional[bool] = False) -> CourseTeacherQuerySet:
    filters = [
        Q(course=course),
        Q(roles=~CourseTeacher.roles.spectator)
    ]
    return get_teachers(role_priority=role_priority, filters=filters)


def course_teachers_prefetch_queryset(*, role_priority: Optional[bool] = True) -> CourseTeacherQuerySet:
    """
    Returns public course teachers sorted by the most priority role
    within the course by default.
    """
    filters = [Q(roles=~CourseTeacher.roles.spectator)]
    queryset = get_teachers(role_priority=role_priority, filters=filters)
    order_by = ['-most_priority_role'] if role_priority else []
    return (queryset
            .only('id', 'course_id', 'teacher_id', 'roles',
                  'teacher__first_name', 'teacher__last_name', 'teacher__patronymic',
                  'teacher__gender', 'teacher__photo', 'teacher__cropbox_data')
            .order_by(*order_by, 'teacher__last_name', 'teacher__first_name'))
