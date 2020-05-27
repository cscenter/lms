import rules
from django.conf import settings

from auth.permissions import Permission
from auth.utils import override_perm
from courses.models import Course
from learning.permissions import EnrollInCourse, EnrollPermissionObject


@rules.predicate
def course_is_open(user, permission_object: EnrollPermissionObject):
    return permission_object.course.is_open


@rules.predicate
def enroll_in_course(user, permission_object: EnrollPermissionObject):
    course = permission_object.course
    student_profile = permission_object.student_profile
    if student_profile.site_id != settings.SITE_ID:
        return False
    if not course.enrollment_is_open:
        return False
    if course.main_branch_id != user.branch_id:
        # Course have to be shared for any club branch to be available
        # on compsciclub.ru
        if course.main_branch.site_id != settings.SITE_ID:
            if not any(branch.site_id == settings.SITE_ID for branch
                       in course.branches.all()):
                return False
    if course.is_capacity_limited and not course.places_left:
        return False
    return True


# FIXME: Only registered users can see the news. What about unauthenticated? Add default role with default permissions
class ClubCourseViewNews(Permission):
    name = "learning.view_course_news"


class ClubEnrollInCourse(EnrollInCourse):
    rule = enroll_in_course & course_is_open


override_perm(ClubCourseViewNews)
override_perm(ClubEnrollInCourse)
