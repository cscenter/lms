# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import os.path

from django.conf import settings
from django.db import models
from django.utils.encoding import python_2_unicode_compatible, smart_text
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from model_utils.fields import StatusField
from model_utils.models import TimeStampedModel

from core.models import LATEX_MARKDOWN_HTML_ENABLED
from learning.models import Semester
from learning.settings import GRADES, PARTICIPANT_GROUPS
from learning.utils import get_current_semester_pair


def studentproject_slides_file_name(self, filename):
    year, type = get_current_semester_pair()
    return os.path.join('project_presentations',
                        '{}-{}'.format(self.semester.year, self.semester.type),
                        filename)


@python_2_unicode_compatible
class StudentProject(TimeStampedModel):
    GRADES = GRADES
    PROJECT_TYPES = Choices(('practice', _("StudentProject|Practice")),
                            ('research', _("StudentProject|Research")))

    name = models.CharField(_("StudentProject|Name"), max_length=255)
    description = models.TextField(
        _("Description"),
        blank=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Students"),
        # XXX: Can generate duplicates here if related user has both groups
        # Unlikely due to admin form validation, but possible in theory
        limit_choices_to={'groups__in': [PARTICIPANT_GROUPS.STUDENT_CENTER,
                                         PARTICIPANT_GROUPS.GRADUATE_CENTER]})

    grade = StatusField(
        verbose_name=_("Grade"),
        choices_name='GRADES',
        default='not_graded')
    supervisor = models.CharField(
        verbose_name=_("StudentProject|Supervisor"),
        max_length=255,
        help_text=_("Format: Last_name First_name Patronymic, Organization"))
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        verbose_name=_("Semester"))
    project_type = models.CharField(
        choices=PROJECT_TYPES,
        verbose_name=_("StudentProject|Type"),
        max_length=10)
    presentation = models.FileField(
        _("Presentation"),
        blank=True,
        upload_to=studentproject_slides_file_name)
    is_external = models.BooleanField(
        _("External project"),
        default=False)

    class Meta:
        # NOTE(Dmitry): we should probably order by min of semesters,
        #               but it can't be enforced here
        ordering = ["name"]
        verbose_name = _("Student project")
        verbose_name_plural = _("Student projects")

    def __str__(self):
        return smart_text(self.name)

    def get_absolute_url(self):
        return self.student.get_absolute_url()

    # this is needed to share code between CourseClasses and this model
    # FIXME: really?!
    @property
    def project_type_display(self):
        return self.PROJECT_TYPES[self.project_type]