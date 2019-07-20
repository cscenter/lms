from enum import Enum, auto

import rules

from auth.permissions import add_perm
from core.utils import is_club_site
from courses.models import Course
from learning.utils import course_failed_by_student
from learning.settings import StudentStatuses
from users.constants import Roles as UserRoles


class LearningPermissionsMixin:
    @property
    def site_groups(self):
        return set()

    @property
    def is_curator(self):
        return self.is_superuser and self.is_staff

    @property
    def is_student(self):
        return UserRoles.STUDENT in self.roles

    @property
    def is_volunteer(self):
        return UserRoles.VOLUNTEER in self.roles

    @property
    def is_expelled(self):
        return None

    # FIXME: inline
    @property
    def is_active_student(self):
        if is_club_site():
            return self.is_student
        has_perm = self.is_student or self.is_volunteer
        return has_perm and self.status != StudentStatuses.EXPELLED

    @property
    def is_teacher(self):
        return UserRoles.TEACHER in self.roles

    @property
    def is_graduate(self):
        return UserRoles.GRADUATE in self.roles

    @property
    def is_curator_of_projects(self):
        return UserRoles.CURATOR_PROJECTS in self.roles

    @property
    def is_interviewer(self):
        return UserRoles.INTERVIEWER in self.roles

    @property
    def is_project_reviewer(self):
        return UserRoles.PROJECT_REVIEWER in self.roles


def has_master_degree(user):
    """
    Emphasis that user is studying for a masters degree.
    This group doesn't give any access to the site.
    """
    return UserRoles.MASTERS_DEGREE in user.roles


class CourseRole(Enum):
    NO_ROLE = auto()
    STUDENT_REGULAR = auto()  # Enrolled active student
    # Restrict access to the course for enrolled students in next cases:
    #   * student failed the course
    #   * student was expelled
    STUDENT_RESTRICT = auto()
    TEACHER = auto()  # Any teacher from the same meta course
    CURATOR = auto()


def course_access_role(*, course, user) -> CourseRole:
    """
    Some course data (e.g. assignments, news) are private and accessible
    depending on the user role: curator, course teacher or
    enrolled student. This UserRoles do not overlap in the same course.
    """
    if not user.is_authenticated:
        return CourseRole.NO_ROLE
    if user.is_curator:
        return CourseRole.CURATOR
    role = CourseRole.NO_ROLE
    enrollment = user.get_enrollment(course.pk)
    if enrollment:
        failed = course_failed_by_student(course, user, enrollment)
        if not failed and not user.is_expelled:
            role = CourseRole.STUDENT_REGULAR
        else:
            role = CourseRole.STUDENT_RESTRICT
    # Teachers from the same course permits to view the news/assignments/etc
    all_course_teachers = (course.course_teachers.field.model.objects
                           .for_course(course.meta_course.slug)
                           .values_list('teacher_id', flat=True))
    if user.is_teacher and user.pk in all_course_teachers:
        # Overrides student role if teacher accidentally enrolled in
        # his own course
        role = CourseRole.TEACHER
    return role


@rules.predicate
def can_view_course_news(user, course: Course):
    role = course_access_role(course=course, user=user)
    return role != CourseRole.NO_ROLE and role != CourseRole.STUDENT_RESTRICT


@rules.predicate
def can_view_course_reviews(user, course: Course):
    return course.enrollment_is_open


@rules.predicate
def can_enroll_in_course(user, course: Course):
    if not course.enrollment_is_open:
        return False
    # If the student can't take this course remotely, check that the city
    # of the student and the city match
    # FIXME: на сайте клуба user.city_id надо заменить на request.city_code :< Как потестировать ещё предикаты сайта клуба?
    if not course.is_correspondence and user.city_id != course.get_city():
        return False
    if course.is_capacity_limited and not course.places_left:
        return False
    return True


add_perm("learning.can_view_course_news", can_view_course_news)
# TODO: Where should live permission below?
add_perm("learning.can_view_course_reviews", can_view_course_reviews)
add_perm("learning.can_enroll_in_course", can_enroll_in_course)
