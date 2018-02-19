from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from social_core.storage import UserMixin
from social_django.models import DjangoStorage


class DjangoStorageCustom(DjangoStorage):
    user = UserMixin


class AdmissionTestApplicant(TimeStampedModel):
    first_name = models.CharField(_("First name"), max_length=255)
    surname = models.CharField(_("Surname"), max_length=255)
    patronymic = models.CharField(_("Patronymic"), max_length=255)
    email = models.EmailField(
        _("Email"),
        help_text=_("Applicant|email"))
    stepic_id = models.PositiveIntegerField(
        _("Stepik ID"),
        help_text=_("Applicant|stepic_id"),
        blank=True,
        null=True)
    yandex_id = models.CharField(
        _("Yandex ID"),
        max_length=80,
        validators=[RegexValidator(regex="^[^@]*$",
                                   message=_("Only the part before "
                                             "\"@yandex.ru\" is expected"))],
        help_text=_("Applicant|yandex_id"),
        null=True,
        blank=True)
    yandex_id_normalize = models.CharField(
        _("Yandex ID normalisation"),
        max_length=80,
        help_text=_("Applicant|yandex_id_normalization"),
        null=True,
        blank=True)
    github_id = models.CharField(
        _("Github ID"),
        max_length=255,
        help_text=_("Applicant|github_id"),
        null=True,
        blank=True)
    uuid = models.UUIDField(editable=False, null=True, blank=True)

    class Meta:
        verbose_name = "Admission Test Applicant"
        verbose_name_plural = "Admission Test Applicants"

    def __str__(self):
        return smart_text(self.get_full_name())

    def get_full_name(self):
        parts = [self.surname, self.first_name, self.patronymic]
        return smart_text(" ".join(part for part in parts if part).strip())

    def clean(self):
        if self.yandex_id:
            self.yandex_id_normalize = self.yandex_id.lower().replace('-', '.')
