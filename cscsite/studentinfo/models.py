# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from model_utils import Choices, FieldTracker
from model_utils.fields import MonitorField, StatusField
from model_utils.managers import QueryManager
from model_utils.models import TimeStampedModel

from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.encoding import smart_text, python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from learning.models import LATEX_MARKDOWN_ENABLED

@python_2_unicode_compatible
class StudentInfo(TimeStampedModel):
    STUDY_PROGRAMS = Choices(('dm', _("Data mining")),
                             ('cs', _("Computer Science")),
                             ('se', _("Software Engineering")))
    STATUS = Choices(('graduate', _("Graduate")),
                     ('expelled', _("StudentInfo|Expelled")),
                     ('reinstated', _("StudentInfo|Reinstalled")),
                     ('will_graduate'), _("StudentInfo|Will graduate"))

    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Student"),
        limit_choices_to={'groups__name': 'Student'},
        on_delete=models.CASCADE)

    university = models.CharField(
        _("University"),
        max_length=140,
        blank=True)
    phone = models.CharField(
        _("Phone"),
        max_length=40,
        blank=True)
    uni_year_at_enrollment = models.PositiveSmallIntegerField(
        _("StudentInfo|University year"),
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        null=True,
        blank=True)
    comment = models.TextField(
        _("Comment"),
        help_text=LATEX_MARKDOWN_ENABLED,
        blank=True)
    # django-simple-history?
    # comment_changed = MonitorField(monitor='comment')
    # comment_last_author = models.ForeignKey(
    #     settings.AUTH_USER_MODEL,
    #     verbose_name=_("Author of last edit"),
    #     on_delete=models.PROTECT,
    #     blank=True)
    nondegree = models.BooleanField(
        _("Non-degree student"),
        default=False)
    status = models.CharField(
        choices=STATUS,
        verbose_name=_("Status"),
        max_length=15,
        blank=True)
    study_program = models.CharField(
        choices=STUDY_PROGRAMS,
        verbose_name=_("StudentInfo|Study program"),
        max_length=2,
        blank=True)
    online_courses = models.TextField(
        _("Online courses"),
        help_text=LATEX_MARKDOWN_ENABLED,
        blank=True)

    class Meta:
        ordering = ["student__name"]
        verbose_name = _("Student info record")
        verbose_name_plural = _("Student info records")

    def __str__(self):
        return smart_text(self.student)
