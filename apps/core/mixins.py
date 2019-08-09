import logging

from django.contrib.contenttypes.models import ContentType
from django.core import checks
from django.db import models
from django.db.models import prefetch_related_objects, FieldDoesNotExist

from .tasks import compute_model_field

logger = logging.getLogger(__name__)


class DerivableFieldsMixin:
    """
    Before computing derivable field value make sure that any data this
    field depends on didn't cache (e.g. related queryset could be cached
    with .prefetch_related)
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
        if not hasattr(self, method_name):
            logger.warning('Try to compute unknown field %s', method_name)
            return False
        try:
            return getattr(self, method_name)()
        except Exception as e:
            logger.exception(e)
        return False

    def compute_fields(self, *derivable_fields, prefetch=False) -> bool:
        """
        Use async version instead to avoid caching problem with .prefetch_related
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
            # FIXME: This one recall save method. Replace with .update?
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


class TimezoneAwareMixin:
    SELF_AWARE = object()
    """
    `TIMEZONE_AWARE_FIELD_NAME = SELF_AWARE` is a special case that means
    current model has all needed data for retrieving timezone value
    """
    def get_timezone(self):
        next_in_tz_aware_mro = getattr(self, self.get_tz_aware_field_name())
        return next_in_tz_aware_mro.get_timezone()

    @classmethod
    def get_tz_aware_field_name(cls):
        return getattr(cls, cls.TIMEZONE_AWARE_FIELD_NAME).field.name

    @classmethod
    def check(cls, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(cls._check_tz_aware_field_declared())
        return errors

    @classmethod
    def _check_tz_aware_field_declared(cls):
        errors = []
        if not hasattr(cls, "TIMEZONE_AWARE_FIELD_NAME"):
            errors.append(
                checks.Error(
                    f'`{cls} is a subclass of TimezoneAwareMixin but no '
                    f'timezone aware information was provided',
                    hint=f'define {cls.__name__}.TIMEZONE_AWARE_FIELD_NAME attribute value',
                    obj=cls,
                    id='timezone.E001',
                ))
        else:
            tz_aware_field_name = cls.TIMEZONE_AWARE_FIELD_NAME
            if tz_aware_field_name is not cls.SELF_AWARE:
                try:
                    tz_aware_field = cls._meta.get_field(tz_aware_field_name)
                    if not issubclass(tz_aware_field.model, TimezoneAwareMixin):
                        errors.append(
                            checks.Error(
                                f"`{cls}`.{tz_aware_field} is not a subclass of TimezoneAwareMixin",
                                hint=f'Make {tz_aware_field} a subclass of TimezoneAwareMixin',
                                obj=cls,
                                id='timezone.E003',
                            ))
                except FieldDoesNotExist:
                    errors.append(
                        checks.Error(
                            f"`{tz_aware_field_name}` is not a valid name for timezone aware field",
                            hint=f'Make sure `{cls.__name__}.TIMEZONE_AWARE_FIELD_NAME` value matches the real field name',
                            obj=cls,
                            id='timezone.E002',
                        ))
        return errors
