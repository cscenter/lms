from __future__ import unicode_literals

from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.utils.encoding import smart_text, python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import cached_property

from sorl.thumbnail import ImageField

import logging

from learning.models import CourseOffering


@python_2_unicode_compatible
class CSCUser(AbstractUser):
    IS_STUDENT_PK = 1
    IS_TEACHER_PK = 2
    IS_GRADUATE_PK = 3

    patronymic = models.CharField(
        _("CSCUser|patronymic"),
        max_length=100,
        blank=True)
    photo = ImageField(
        _("CSCUser|photo"),
        upload_to="photos/",
        blank=True)
    note = models.TextField(
        _("CSCUser|note"),
        help_text=_("LaTeX+Markdown is enabled"),
        blank=True)
    enrollment_year = models.PositiveSmallIntegerField(
        _("CSCUser|enrollment year"),
        validators=[MinValueValidator(1990)],
        blank=True,
        null=True)
    graduation_year = models.PositiveSmallIntegerField(
        _("CSCUser|graduation year"),
        blank=True,
        validators=[MinValueValidator(1990)],
        null=True)
    yandex_id = models.CharField(
        _("Yandex ID"),
        max_length=80,
        validators=[RegexValidator(regex="^[^@]*$",
                                   message=_("Only the part before "
                                             "\"@yandex.ru\" is expected"))],
        blank=True)
    stepic_id = models.PositiveSmallIntegerField(
        _("Stepic ID"),
        blank=True,
        null=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = _("CSCUser|user")
        verbose_name_plural = _("CSCUser|users")

    def clean(self):
        # avoid checking if the model wasn't yet saved, otherwise exception
        # will be thrown about missing many-to-many relation
        if self.pk:
            if self.is_student and self.enrollment_year is None:
                raise ValidationError(_("CSCUser|enrollment year should be "
                                        "provided for students"))
            if self.is_graduate and self.graduation_year is None:
                raise ValidationError(_("CSCUser|graduation year should be "
                                        " provided for graduates"))

    def get_full_name(self):
        parts = [self.first_name,
                 self.patronymic,
                 self.last_name]
        full_name = smart_text(" "
                               .join(part for part in parts if part)
                               .strip())
        return full_name or self.username

    def __str__(self):
        return smart_text(self.get_full_name())

    def get_absolute_url(self):
        return reverse('user_detail', args=[self.pk])

    @cached_property
    def _cs_group_pks(self):
        return self.groups.values_list("pk", flat=True)

    @property
    def is_student(self):
        return self.IS_STUDENT_PK in self._cs_group_pks

    @property
    def is_teacher(self):
        return self.IS_TEACHER_PK in self._cs_group_pks

    @property
    def is_graduate(self):
        return self.IS_GRADUATE_PK in self._cs_group_pks
