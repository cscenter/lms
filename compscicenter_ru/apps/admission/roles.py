from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C

from auth.registry import role_registry


class Roles(DjangoChoices):
    INTERVIEWER = C(7, _('Interviewer [Admission]'), permissions=(
        "learning.view_admission_menu",
    ))


role_registry.register(Roles.INTERVIEWER,
                       Roles.get_choice(Roles.INTERVIEWER).permissions)
