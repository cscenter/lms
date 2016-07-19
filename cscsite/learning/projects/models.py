# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import os.path

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.encoding import python_2_unicode_compatible, smart_text
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from model_utils.models import TimeStampedModel

from core.models import LATEX_MARKDOWN_HTML_ENABLED
from learning.models import Semester
from learning.settings import GRADES, PARTICIPANT_GROUPS


def project_slides_file_name(self, filename):
    return os.path.join('project_presentations',
                        '{}-{}'.format(self.semester.year, self.semester.type),
                        filename)


@python_2_unicode_compatible
class ProjectStudent(models.Model):
    GRADES = GRADES
    student = models.ForeignKey(settings.AUTH_USER_MODEL)
    project = models.ForeignKey('Project')
    supervisor_grade = models.SmallIntegerField(
        verbose_name=_("Supervisor grade"),
        validators=[MinValueValidator(-15), MaxValueValidator(15)],
        blank=True,
        null=True)
    supervisor_review = models.TextField(
        _("Review from supervisor"),
        blank=True)
    presentation_grade = models.PositiveSmallIntegerField(
        verbose_name=_("Presentation grade"),
        validators=[MaxValueValidator(10)],
        blank=True,
        null=True)
    final_grade = models.CharField(
        verbose_name=_("Final grade"),
        choices=GRADES,
        max_length=15,
        default=GRADES.not_graded)

    class Meta:
        verbose_name = _("Project student")
        verbose_name_plural = _("Project students")
        unique_together = [['student', 'project']]

    def __str__(self):
        return "{0} [{1}]".format(smart_text(self.project),
                                  smart_text(self.student))


@python_2_unicode_compatible
class Project(TimeStampedModel):
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
        # XXX: Admin can generate duplicates if user has both groups
        limit_choices_to={'groups__in': [PARTICIPANT_GROUPS.STUDENT_CENTER,
                                         PARTICIPANT_GROUPS.GRADUATE_CENTER]},
        through=ProjectStudent)
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
        upload_to=project_slides_file_name)
    is_external = models.BooleanField(
        _("External project"),
        default=False)

    class Meta:
        verbose_name = _("Student project")
        verbose_name_plural = _("Student projects")

    def __str__(self):
        return smart_text(self.name)

    def get_absolute_url(self):
        return self.student.get_absolute_url()
