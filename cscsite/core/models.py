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

    class Meta:
        verbose_name = _("CSCUser|user")
        verbose_name_plural = _("CSCUser|users")

    def clean(self):
        print self.groups
        pass

    # TODO: test this
    def get_full_name(self):
        return force_text("{0} {1} {2}".format(self.last_name,
                                               self.first_name,
                                               self.patronymic).strip())
