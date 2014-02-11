from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from django.utils.functional import cached_property

from sorl.thumbnail import ImageField

import logging

class CSCUser(AbstractUser):
    IS_STUDENT_PK = 1
    IS_TEACHER_PK = 2
    IS_GRADUATE_PK = 3

    patronymic = models.CharField(
        _("CSCUser|patronymic"),
        max_length=100,
        blank=True)

    # TODO: come up with something clever for resizing/validation here
    photo = ImageField(
        _("CSCUser|photo"),
        upload_to="photos/",
        blank=True)

    note = models.TextField(
        _("CSCUser|note"),
        help_text=_("LaTeX+Markdown is enabled"),
        blank=True)

    enrolment_year = models.PositiveSmallIntegerField(
        _("CSCUser|enrolment year"),
        validators=[MinValueValidator(1990)],
        blank=True,
        null=True)

    graduation_year = models.PositiveSmallIntegerField(
        _("CSCUser|graduation year"),
        validators=[MinValueValidator(1990)],
        blank=True,
        null=True)

    class Meta:
        verbose_name = _("CSCUser|user")
        verbose_name_plural = _("CSCUser|users")

    def clean(self):
        # avoid checking if the model wasn't yet saved, otherwise exception
        # will be thrown about missing many-to-many relation
        if self.pk:
            if self.is_student and self.enrolment_year is None:
                raise ValidationError(_("CSCUser|enrolment year should be "
                                        "provided for students"))
            if self.is_graduate and self.graduation_year is None:
                raise ValidationError(_("CSCUser|graduation year should be "
                                        " provided for graduates"))

    def get_full_name(self):
        return force_text(u"{0} {1} {2}".format(self.last_name,
                                                self.first_name,
                                                self.patronymic).strip())

    @cached_property
    def _cs_group_pks(self):
        return [group.pk for group in self.groups.all()]

    @property
    def is_student(self):
        return self.IS_STUDENT_PK in self._cs_group_pks

    @property
    def is_teacher(self):
        return self.IS_TEACHER_PK in self._cs_group_pks

    @property
    def is_graduate(self):
        return self.IS_GRADUATE_PK in self._cs_group_pks
