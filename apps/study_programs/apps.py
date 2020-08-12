from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class StudyProgramsConfig(AppConfig):
    name = 'study_programs'
    verbose_name = _("Study Programs")
