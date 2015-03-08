# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.db import models


@python_2_unicode_compatible
class EnrollmentApplicationEmail(TimeStampedModel):
    email = models.EmailField(_("email"))
    is_notified = models.BooleanField(_("User is notified"),
                                      default=False)

    class Meta:
        ordering = ["email"]
        verbose_name = _("Enrollment application email")
        verbose_name_plural = _("Enrollment application emails")

    def __str__(self):
        return smart_text(self.email)
