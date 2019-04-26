from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, C


class ProjectTypes(DjangoChoices):
    practice = C('practice', _("StudentProject|Practice"))
    research = C('research', _("StudentProject|Research"))
