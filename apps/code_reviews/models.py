from django.contrib.sites.models import Site
from django.db import models
from django.utils.translation import gettext_lazy as _

from learning.models import StudentAssignment


class GerritChange(models.Model):
    student_assignment = models.OneToOneField(
        StudentAssignment,
        verbose_name=_('Student Assignment'),
        on_delete=models.CASCADE
    )
    change_id = models.CharField(
        max_length=255,
        help_text=_('Full ID of the change in Gerrit: `{project_name}~{branch_name}~{change_id}`')
    )
    site = models.ForeignKey(
        Site, on_delete=models.CASCADE,
        related_name='+'
    )

    def __str__(self):
        return f'{self.site.name} - {self.change_id}'

    class Meta:
        verbose_name = _('Gerrit Change')
        verbose_name_plural = _('Gerrit Changes')
