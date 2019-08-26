import rules

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


override_perm("learning.view_course_news", rules.always_true)
override_perm("learning.enroll_in_course", enroll_in_course & course_is_open)
