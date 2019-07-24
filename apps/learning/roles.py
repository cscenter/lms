from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C

from auth.registry import role_registry


# TODO: Add description of each role
class Roles(DjangoChoices):
    STUDENT = C(1, _('Student'), permissions=(
        "courses.can_view_contacts",
        "courses.can_view_assignments",
        "learning.can_view_course_news",
        "learning.can_view_course_reviews",
        "learning.can_enroll_in_course",
    ))
    TEACHER = C(2, _('Teacher'), permissions=(
        "courses.can_view_contacts",
        "courses.can_view_assignments",
        "learning.can_view_course_news",
    ))
    GRADUATE = C(3, _('Graduate'))
    VOLUNTEER = C(4, _('Volunteer'), permissions=(
        "courses.can_view_contacts",
        "courses.can_view_assignments",
        "learning.can_view_course_news",
        "learning.can_view_course_reviews",
        "learning.can_enroll_in_course",
    ))
    CURATOR = C(5, _('Curator'), permissions=(
        "courses.change_metacourse",
        "courses.can_view_contacts",
        "courses.can_view_assignments",
        "learning.can_view_course_news",
        "learning.can_view_course_reviews"
    ))
    INVITED = C(11, _('Invited User'), permissions=(
        "courses.can_view_contacts",
        "courses.can_view_assignments",
        "learning.can_view_course_news",
        "learning.can_view_course_reviews"
    ))


role_registry.register(Roles.STUDENT,
                       Roles.get_choice(Roles.STUDENT).permissions)
role_registry.register(Roles.TEACHER,
                       Roles.get_choice(Roles.TEACHER).permissions)
role_registry.register(Roles.VOLUNTEER,
                       Roles.get_choice(Roles.VOLUNTEER).permissions)
role_registry.register(Roles.CURATOR,
                       Roles.get_choice(Roles.CURATOR).permissions)
role_registry.register(Roles.INVITED,
                       Roles.get_choice(Roles.INVITED).permissions)
