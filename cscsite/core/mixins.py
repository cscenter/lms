import logging

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import prefetch_related_objects

logger = logging.getLogger(__name__)


class DerivableFieldsMixin:
    """
    Before computing any field value make sure that data this field depends on
    didn't cache (e.g. related queryset could be cached with .prefetch_related)
    """
    derivable_fields = []
    prefetch_before_compute_fields = {}

    @classmethod
    def prefetch_before_compute(cls, *derivable_fields):
        prefetch_fields = set()

        for field in derivable_fields:
            fields = cls.prefetch_before_compute_fields.get(field)
            if fields:
                prefetch_fields.update(fields)

        return prefetch_fields

    def _call_compute_method(self, method_name):
        try:
            return getattr(self, method_name)()
        except AttributeError:
            logger.warning('Try to compute unknown field %s', method_name)
        return False

    def compute_fields(self, *derivable_fields, prefetch=False) -> bool:
        """
        Use async version to avoid caching problem with .prefetch_related
        """
        if not isinstance(self, models.Model):
            raise TypeError('DerivableFieldsMixin needs a model instance')

        if self.pk is None:
            raise ValueError('Model should be already saved')

        if prefetch:
            prefetch_fields = self.prefetch_before_compute(*derivable_fields)
            if prefetch_fields:
                prefetch_related_objects((self,), *prefetch_fields)

        derived_fields = []
        derivable_fields = derivable_fields or self.derivable_fields

        for field in derivable_fields:
            compute_method_name = '_compute_{}'.format(field)

            if self._call_compute_method(compute_method_name):
                derived_fields.append(field)

        if derived_fields:
            self.save(update_fields=derived_fields)
            return True

        return False

    def compute_fields_async(self, *derivable_fields) -> None:
        if not isinstance(self, models.Model):
            raise TypeError('DerivableFieldsMixin needs a model instance')

        content_type = ContentType.objects.get_for_model(self)
        derivable_fields = derivable_fields or self.derivable_fields

        for field in derivable_fields:
            compute_model_field.delay(content_type.id, self.pk, field)