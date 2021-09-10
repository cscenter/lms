from django.db import models


class EmailAddressSuspension(models.Model):
    email_suspension_details = models.JSONField(
        verbose_name="Email Address Suspension Details",
        blank=True, null=True,
        editable=False)

    class Meta:
        abstract = True
