import rules

from auth.permissions import all_permissions, add_perm
from learning.permissions import enroll_in_course

# Override permissions to meet compsciclub.ru requirements
all_permissions.remove_rule("learning.view_course_news")
all_permissions.remove_rule("learning.enroll_in_course")


@rules.predicate
def course_is_open(user, course):
    return course.is_open


add_perm("learning.view_course_news", rules.always_true)
add_perm("learning.enroll_in_course", enroll_in_course & course_is_open)
