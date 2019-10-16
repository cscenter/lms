import rules

from auth.permissions import Permission
from auth.utils import override_perm
from courses.models import Course


@rules.predicate
def course_is_open(user, course):
    return course.is_open


@rules.predicate
def enroll_in_course(user, course: Course):
    if not course.enrollment_is_open:
        return False
    # Check that course is available for student branch
    if course.branch_id != user.branch_id:
        if user.branch not in course.additional_branches.all():
            return False
    if course.is_capacity_limited and not course.places_left:
        return False
    return True


# FIXME: Only registered users can see the news. What about unauthenticated? Add default role with default permissions
class ClubCourseViewNews(Permission):
    name = "learning.view_course_news"


class ClubEnrollInCourse(Permission):
    name = "learning.enroll_in_course"
    rule = enroll_in_course & course_is_open


override_perm(ClubCourseViewNews)
override_perm(ClubEnrollInCourse)
