from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C

from auth.permissions import Role
from auth.registry import role_registry


class Roles(DjangoChoices):
    INTERVIEWER = C(7, _('Interviewer [Admission]'), permissions=(
        "learning.view_admission_menu",
    ))


for code, name in Roles.choices:
    role_registry.register(Role(code=code, name=name,
                                permissions=Roles.get_choice(code).permissions))
