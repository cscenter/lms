import logging
from typing import TYPE_CHECKING, Iterable, Mapping, Set

from django.core import checks
from django.db import models
from django.db.models import prefetch_related_objects

from core.tasks import compute_model_fields

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    ModelMixinBase = models.Model
else:
    ModelMixinBase = object


class DerivableFieldsMixin(ModelMixinBase):
    """
    Before computing derivable field value make sure that any data this
    field depends on didn't cache (e.g. related queryset could be cached
    with .prefetch_related)
    """
    # TODO: Make as an abstract property
    derivable_fields: Iterable[str] = []
    prefetch_before_compute_fields: Mapping[str, Iterable[str]] = {}

    @classmethod
    def prefetch_before_compute(cls, *derivable_fields):
        prefetch_fields: Set[str] = set()

        for field in derivable_fields:
            fields = cls.prefetch_before_compute_fields.get(field)
            if fields:
                prefetch_fields.update(fields)

        return prefetch_fields

    def _call_compute_method(self, method_name):
        if not hasattr(self, method_name):
            logger.warning('Try to compute unknown field %s', method_name)
            return False
        try:
            return getattr(self, method_name)()
        except Exception as e:
            logger.exception(e)
        return False

    def compute_fields(self, *derivable_fields: str, prefetch=False,
                       commit=True) -> bool:
        """
        Use async version to avoid caching problem with `.prefetch_related`
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

        for field in derivable_fields or self.derivable_fields:
            compute_method_name = '_compute_{}'.format(field)

            if self._call_compute_method(compute_method_name):
                derived_fields.append(field)

        if derived_fields:
            if commit:
            # FIXME: This one recall save method. Replace with .update?
                self.save(update_fields=derived_fields)
            return True

        return False

    def compute_fields_async(self, *derivable_fields) -> None:
        from django.contrib.contenttypes.models import ContentType
        if not isinstance(self, models.Model):
            raise TypeError('DerivableFieldsMixin needs a model instance')

        content_type = ContentType.objects.get_for_model(self)
        # FIXME: investigate do we need transaction.on_commit here or not
        compute_model_fields.delay(content_type.id, self.pk, derivable_fields)

    @classmethod
    def check(cls, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(cls._check_mixin_contract())
        return errors

    @classmethod
    def _check_mixin_contract(cls):
        from collections.abc import Iterable
        errors = []
        if not issubclass(cls, models.Model):
            errors.append(  # type: ignore[unreachable]
                checks.Error(
                    f'`{cls.__name__} is a subclass of DerivableFieldsMixin '
                    f'and must be a subclass of django.db.models.Model as well',
                    obj=cls,
                    id='derivable_mixin.E001',
                ))
        if not hasattr(cls, "derivable_fields"):
            errors.append(
                checks.Error(
                    f'`{cls} is a subclass of DerivableFieldsMixin but no '
                    f'information about derivable fields was provided',
                    hint=f'define {cls.__name__}.derivable_fields attribute',
                    obj=cls,
                    id='derivable_mixin.E002',
                ))
        if not isinstance(cls.derivable_fields, Iterable):
            errors.append(
                checks.Error(
                    f'`{cls.__name__}.derivable_fields must be iterable',
                    obj=cls,
                    id='derivable_mixin.E003',
                ))
        return errors
