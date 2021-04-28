from model_utils.models import TimeStampedModel

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .settings import DIGEST_MAX_LENGTH, TOKEN_KEY_LENGTH


class Token(TimeStampedModel):
    """
    This model doesn't store token as a plain text
    """
    digest = models.CharField(
        max_length=DIGEST_MAX_LENGTH, primary_key=True)
    access_key = models.CharField(
        verbose_name=_("Access Key"),
        max_length=TOKEN_KEY_LENGTH,
        db_index=True,
        help_text=_("First %s symbols of the secret key") % TOKEN_KEY_LENGTH)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("User"),
        related_name='api_tokens',
        on_delete=models.CASCADE)
    expire_at = models.DateTimeField(
        verbose_name=_("Expire at"),
        null=True, blank=True)

    class Meta:
        db_table = 'api_tokens'
        verbose_name = _("Token")
        verbose_name_plural = _("Tokens")

    def __str__(self):
        return '%s : %s' % (self.access_key, self.user)
