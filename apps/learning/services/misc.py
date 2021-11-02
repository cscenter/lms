from enum import Enum, auto

from learning.services.enrollment_service import is_course_failed_by_student
from learning.settings import StudentStatuses
from users.constants import Roles


class CourseRole(Enum):
    NO_ROLE = auto()
    STUDENT_REGULAR = auto()  # Enrolled active student
    # Restrict access to the course for enrolled students in next cases:
    #   * student failed the course
    #   * student was expelled or in academic leave
    STUDENT_RESTRICT = auto()
    TEACHER = auto()  # Any teacher from the same meta course
    CURATOR = auto()


def course_access_role(*, course, user) -> CourseRole:
    """
    Some course data (e.g. assignments, news) are private and accessible
    depending on the user role: curator, course teacher or
    enrolled student. This roles do not overlap in the same course.
    """
    if not user.is_authenticated:
        return CourseRole.NO_ROLE
    if user.is_curator:
        return CourseRole.CURATOR
    role = CourseRole.NO_ROLE
    enrollment = user.get_enrollment(course.pk)
    if enrollment:
        failed = is_course_failed_by_student(course, user, enrollment)
        student_status = enrollment.student_profile.status
        if not failed and not StudentStatuses.is_inactive(student_status):
            role = CourseRole.STUDENT_REGULAR
        else:
            role = CourseRole.STUDENT_RESTRICT
    # FIXME: separate into teacher_spectator and teacher_regular?
    if Roles.TEACHER in user.roles and user in course.teachers.all():
        # Teacher role has a higher precedence
        role = CourseRole.TEACHER
    return role
