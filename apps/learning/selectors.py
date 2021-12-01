from typing import List, Union

from django.db.models import Q, QuerySet

from courses.managers import AssignmentQuerySet, CourseClassQuerySet, CourseQuerySet
from courses.models import Assignment, Course, CourseClass, CourseTeacher
from learning.managers import EnrollmentQuerySet
from learning.models import Enrollment, Event
from users.models import User

CourseID = int


def get_teacher_courses(teacher: User) -> CourseQuerySet:
    return (Course.objects
            .filter(teachers=teacher)
            .select_related("meta_course", "semester", "main_branch"))


def get_teacher_not_spectator_courses(teacher: User) -> CourseQuerySet:
    return (Course.objects
            .filter(teachers=teacher,
                    course_teachers__roles=~CourseTeacher.roles.spectator)
            .select_related("meta_course", "semester", "main_branch"))


def get_course_assignments(course: Union[CourseID, Course]) -> AssignmentQuerySet:
    return (Assignment.objects
            .filter(course=course))


def get_active_enrollments(course: Union[CourseID, Course]) -> EnrollmentQuerySet:
    return (Enrollment.active
            .filter(course=course))


def get_student_classes(user, filters: List[Q] = None,
                        with_venue=False) -> CourseClassQuerySet:
    # Student could be manually enrolled in the course without
    # checking branch compatibility, skip filtering by branch
    branch_list = []
    qs = (get_classes(branch_list, filters)
          .for_student(user)
          .order_by("-date", "-starts_at"))
    if with_venue:
        qs = qs.select_related('venue', 'venue__location')
    return qs


# TODO: move to courses.selectors
def get_teacher_classes(user, filters: List[Q] = None,
                        with_venue=False) -> CourseClassQuerySet:
    branch_list = []
    qs = get_classes(branch_list, filters).for_teacher(user)
    if with_venue:
        qs = qs.select_related('venue', 'venue__location')
    return qs


def get_classes(branch_list, filters: List[Q] = None) -> CourseClassQuerySet:
    filters = filters or []
    return (CourseClass.objects
            .filter(*filters)
            .in_branches(*branch_list)
            .select_calendar_data())


def get_study_events(filters: List[Q] = None) -> QuerySet:
    filters = filters or []
    return (Event.objects
            .filter(*filters)
            .select_related('venue')
            .order_by('date', 'starts_at'))


def get_teacher_assignments(user):
    """
    Returns assignments where user is participating as a teacher.
    """
    return (Assignment.objects
            .filter(course__teachers=user,
                    course__course_teachers__roles=~CourseTeacher.roles.spectator)
            .select_related('course',
                            'course__meta_course',
                            'course__semester'))
