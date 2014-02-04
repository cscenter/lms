from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from sorl.thumbnail import ImageField

class CSCUser(AbstractUser):
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

    @property
    def is_student(self):
        return self.groups.filter(name="Student").exists()

    @property
    def is_teacher(self):
        return self.groups.filter(name="Teacher").exists()

    @property
    def is_graduate(self):
        return self.groups.filter(name="Graduate").exists()

    def clean(self):
        if self.is_student and self.enrolment_year is None:
            raise ValidationError(_("CSCUser|enrolment year should be provided "
                                    "for students"))
        if self.is_graduate and self.graduation_year is None:
            raise ValidationError(_("CSCUser|graduation year should be provided "
                                    "for graduates"))
    def get_full_name(self):
        return force_text(u"{0} {1} {2}".format(self.last_name,
                                                self.first_name,
                                                self.patronymic).strip())
