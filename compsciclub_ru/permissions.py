import rules
from rules import predicate

from auth.permissions import all_permissions
from auth.registry import role_registry
from courses.models import Course


def override_perm(name, pred=None):
    """
    Override permissions to meet compsciclub.ru requirements:
        update global permissions rule set
        update already registered roles which have ref to the old permission
    """
    if not all_permissions.rule_exists(name):
        return
    if pred is None:
        pred = predicate(lambda: True, name=name)
    all_permissions.set_rule(name, pred)
    for _, role_perms in role_registry.items():
        if role_perms.rule_exists(name):
            role_perms.set_rule(name, pred)


@rules.predicate
def course_is_open(user, course):
    return course.is_open


@rules.predicate
def enroll_in_course(user, course: Course):
    if not course.enrollment_is_open:
        return False
    # If the student can't take this course remotely, check that the city
    # of the student and the city match
    # FIXME: что-то надо с этим сделать
    #if not course.is_correspondence and user.city_id != course.get_city():
    #    return False
    if course.is_capacity_limited and not course.places_left:
        return False
    return True


override_perm("learning.view_course_news", rules.always_true)
override_perm("learning.enroll_in_course", enroll_in_course & course_is_open)
