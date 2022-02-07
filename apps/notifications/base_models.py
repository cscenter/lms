from django.db import models


class EmailAddressSuspension(models.Model):
    email_suspension_details = models.JSONField(
        verbose_name="Email Address Suspension Details",
        blank=True, null=True,
        editable=False)

    @property
    def is_email_suspended(self):
        return (isinstance(self.email_suspension_details, dict) and
                self.email_suspension_details.get('bounceType') == 'Permanent')

    class Meta:
        abstract = True
