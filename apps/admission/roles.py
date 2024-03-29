from djchoices import C, DjangoChoices

from django.utils.translation import gettext_lazy as _

from auth.permissions import Role
from auth.registry import role_registry

from .permissions import ViewAdmissionMenu


class Roles(DjangoChoices):
    INTERVIEWER = C(7, _("Interviewer [Admission]"), permissions=(ViewAdmissionMenu,))


for code, name in Roles.choices:
    role_registry.register(
        Role(
            id=code,
            code=code,
            description=name,
            permissions=Roles.get_choice(code).permissions,
        )
    )
