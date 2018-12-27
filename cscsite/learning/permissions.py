from enum import Enum, auto
from typing import Optional

from core.utils import is_club_site
from learning.enrollment import course_failed_by_student
from learning.settings import StudentStatuses
from users.constants import AcademicRoles


class LearningPermissionsMixin:
    @property
    def _cached_groups(self):
        return set()

    def get_cached_groups(self):
        return self._cached_groups

    @property
    def is_student(self):
        if is_club_site():
            return self.is_student_club
        return self.is_student_center or self.is_volunteer

    @property
    def is_expelled(self):
        return None

    @property
    def is_student_center(self):
        return AcademicRoles.STUDENT_CENTER in self._cached_groups

    @property
    def is_student_club(self):
        return AcademicRoles.STUDENT_CLUB in self._cached_groups

    @property
    def is_active_student(self):
        if is_club_site():
            return self.is_student_club
        return self.is_student and self.status != StudentStatuses.EXPELLED

    @property
    def is_teacher(self):
        return self.is_teacher_center or self.is_teacher_club

    @property
    def is_teacher_club(self):
        return AcademicRoles.TEACHER_CLUB in self._cached_groups

    @property
    def is_teacher_center(self):
        return AcademicRoles.TEACHER_CENTER in self._cached_groups

    @property
    def is_graduate(self):
        return AcademicRoles.GRADUATE_CENTER in self._cached_groups

    @property
    def is_volunteer(self):
        return AcademicRoles.VOLUNTEER in self._cached_groups

    @property
    def is_master_student(self):
        """
        Studying for a masters degree. Student with this group should be
        center student or volunteer.
        """
        return AcademicRoles.MASTERS_DEGREE in self._cached_groups

    @property
    def is_curator(self):
        return self.is_superuser and self.is_staff

    @property
    def is_curator_of_projects(self):
        return AcademicRoles.CURATOR_PROJECTS in self._cached_groups

    @property
    def is_interviewer(self):
        return AcademicRoles.INTERVIEWER in self._cached_groups

    @property
    def is_project_reviewer(self):
        return AcademicRoles.PROJECT_REVIEWER in self._cached_groups


class CourseRole(Enum):
    NO_ROLE = auto()
    STUDENT_REGULAR = auto()  # Enrolled active student
    # Restrict access to the course for enrolled students in next cases:
    #   * student failed the course
    #   * student was expelled
    STUDENT_RESTRICT = auto()
    TEACHER = auto()  # Any teacher from the same meta course
    CURATOR = auto()


def course_access_role(*, course, request_user) -> CourseRole:
    """
    Some course data (e.g. assignments, news) are private and accessible
    depending on the user role: curator, course teacher or
    enrolled student. This roles do not overlap in the same course.

    Returns request user role in target course session,
    `None` is user has no access at all.

    FIXME: enrolled students who was expelled have no access at all right now
    """
    if not request_user.is_authenticated or request_user.is_expelled:
        return CourseRole.NO_ROLE
    if request_user.is_curator:
        return CourseRole.CURATOR
    role = CourseRole.NO_ROLE
    enrollment = request_user.get_enrollment(course.pk)
    if enrollment:
        if not course_failed_by_student(course, request_user, enrollment):
            role = CourseRole.STUDENT_REGULAR
        else:
            role = CourseRole.STUDENT_RESTRICT
    # Teachers from the same course permits to view the news/assignments/etc
    all_course_teachers = (course.course_teachers.field.model.objects
                           .for_course(course.meta_course.slug)
                           .values_list('teacher_id', flat=True))
    if request_user.is_teacher and request_user.pk in all_course_teachers:
        # Overrides student role if teacher accidentally enrolled in
        # his own course
        role = CourseRole.TEACHER
    return role
