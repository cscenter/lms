from model_utils.models import TimeStampedModel

from django.conf import settings
from django.db import models, router
from django.utils.translation import gettext_lazy as _


class ConfigurationModel(TimeStampedModel):
    """Abstract base class for model-based configuration"""

    enabled = models.BooleanField(default=False, verbose_name=_("Enabled"))
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        editable=False,
        null=True,
        on_delete=models.PROTECT,
        verbose_name=_("Changed by"))

    class Meta:
        abstract = True


class LiveManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class TrashManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=False)


class SoftDeletionModel(models.Model):
    """Abstract base class for model soft deletion"""
    deleted_at = models.DateTimeField(db_index=True, blank=True, null=True)

    objects = LiveManager()
    trash = TrashManager()
    base = models.Manager()

    class Meta:
        abstract = True

    @property
    def is_deleted(self):
        return bool(self.deleted_at)

    def delete(self, using=None, permanent=False):
        from core.services import SoftDeleteService
        if permanent:
            super().delete(using=using, keep_parents=False)
        else:
            using = using or router.db_for_write(self.__class__, instance=self)
            assert self.pk is not None, (
                "%s object can't be deleted because its %s attribute is set to None." %
                (self._meta.object_name, self._meta.pk.attname)  # type: ignore[union-attr]
            )
            SoftDeleteService(using).delete([self])

    def restore(self, using=None):
        from core.services import SoftDeleteService
        if self.deleted_at:
            using = using or router.db_for_write(self.__class__, instance=self)
            SoftDeleteService(using).restore([self])
