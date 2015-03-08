# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.db import models
from django.utils.encoding import smart_text, python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from model_utils.models import TimeStampedModel


@python_2_unicode_compatible
class EnrollmentApplEmail(TimeStampedModel):
    email = models.EmailField(_("email"))
    is_notified = models.BooleanField(_("User is notified"),
                                      default=False)

    class Meta:
        ordering = ["email"]
        verbose_name = _("Enrollment application email")
        verbose_name_plural = _("Enrollment application emails")

    def __str__(self):
        return smart_text(self.email)
