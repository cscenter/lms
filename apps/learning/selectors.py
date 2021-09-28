from typing import Union

from courses.managers import AssignmentQuerySet, CourseQuerySet
from courses.models import Assignment, Course
from learning.managers import EnrollmentQuerySet
from learning.models import Enrollment
from users.models import User

CourseID = int


def get_teacher_courses(teacher: User) -> CourseQuerySet:
    return (Course.objects
            .filter(teachers=teacher)
            .select_related("meta_course", "semester", "main_branch"))


def get_course_assignments(course: Union[CourseID, Course]) -> AssignmentQuerySet:
    return (Assignment.objects
            .filter(course=course))


def get_active_enrollments(course: Union[CourseID, Course]) -> EnrollmentQuerySet:
    return (Enrollment.active
            .filter(course=course))
