import rules

from auth.permissions import add_perm
from courses.models import Course


@rules.predicate
def can_view_course_contacts(user, course: Course):
    return True


@rules.predicate
def can_view_course_assignments(user, course: Course):
    return True


add_perm("courses.can_view_news")
add_perm("courses.can_view_contacts", can_view_course_contacts)
add_perm("courses.can_view_assignments", can_view_course_assignments)

