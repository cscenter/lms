from django.utils.translation import gettext_lazy as _
from djchoices import DjangoChoices, C

from auth.permissions import Role
from auth.registry import role_registry
from learning.permissions import EditStudentAssignment


class Roles(DjangoChoices):
    SERVICE_USER = C(12, _('Service User'), permissions=(
        EditStudentAssignment
    ))


for code, name in Roles.choices:
    role_registry.register(Role(code=code, name=name,
                                permissions=Roles.get_choice(code).permissions))
