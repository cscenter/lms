from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C

from auth.registry import role_registry


class Roles(DjangoChoices):
    STUDENT = C(1, _('Student'), permissions=(
        "courses.can_view_contacts",
        "courses.can_view_assignments",
    ))


role_registry.register(Roles.STUDENT,
                       Roles.get_choice(Roles.STUDENT).permissions)
