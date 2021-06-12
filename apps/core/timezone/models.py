from typing import Optional

from django.core import checks
from django.core.exceptions import FieldDoesNotExist

from .typing import Timezone

__all__ = ['TimezoneAwareMixin']


class TimezoneAwareMixin:
    def get_timezone(self) -> Optional[Timezone]:
        related_field = getattr(self, self.TIMEZONE_AWARE_FIELD_NAME)
        if isinstance(related_field, TimezoneAwareMixin):
            return related_field.get_timezone()
        return related_field

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
            if 'get_timezone' in cls.__dict__:
                errors.append(
                    checks.Warning(
                        f"class {cls.__name__} overrides `get_timezone` method",
                        hint=f'Remove `get_timezone` method from {cls} to restore default behavior',
                        obj=cls,
                        id='timezone.E005',
                    ))
            tz_aware_field = None
            tz_aware_field_name = cls.TIMEZONE_AWARE_FIELD_NAME
            try:
                tz_aware_field = cls._meta.get_field(tz_aware_field_name)
            except FieldDoesNotExist:
                errors.append(
                    checks.Error(
                        f"`{tz_aware_field_name}` is not a valid name for timezone aware field",
                        hint=f'Make sure `{cls.__name__}.TIMEZONE_AWARE_FIELD_NAME` value matches the real field name',
                        obj=cls,
                        id='timezone.E002',
                    ))
            if tz_aware_field is not None:
                related_model = tz_aware_field.related_model
                if related_model is not None and not issubclass(related_model, TimezoneAwareMixin):
                    errors.append(
                        checks.Error(
                            f"`{cls}`.{tz_aware_field} is not a subclass of TimezoneAwareMixin",
                            hint=f'Make {tz_aware_field} a subclass of TimezoneAwareMixin',
                            obj=cls,
                            id='timezone.E003',
                        ))
                errors.extend(cls._check_get_timezone_mro())
        return errors

    @classmethod
    def _check_get_timezone_mro(cls):
        """Detect cycles and make sure `get_timezone` is terminated."""
        errors = []
        next_cls = cls
        next_field_name = next_cls.TIMEZONE_AWARE_FIELD_NAME
        next_field = next_cls._meta.get_field(next_field_name)
        while next_field.related_model is not None:
            try:
                next_cls = next_field.related_model
                next_field_name = next_cls.TIMEZONE_AWARE_FIELD_NAME
                next_field = next_cls._meta.get_field(next_field_name)
            except (FieldDoesNotExist, AttributeError):
                errors.append(
                    checks.Error(
                        f"Runtime error on detecting cycle and termination for `{cls.__name__}` class.",
                        hint=f'Fix timezone.XXX errors for {next_cls} class',
                        obj=cls,
                        id='timezone.E006',
                    ))
                break
            if next_cls is cls:
                errors.append(
                    checks.Error(
                        f"Cycle detected for `{cls.__name__}` class in `get_timezone` mro chain",
                        hint=f'`get_timezone` method for {next_cls} class should terminate.',
                        obj=cls,
                        id='timezone.E007',
                    ))
                break
            if next_cls is TimezoneAwareMixin:
                errors.append(
                    checks.Error(
                        f"`{cls.__name__}` is not terminated properly",
                        hint=f'Define TIMEZONE_AWARE_FIELD_NAME in mro call chain for {cls} that resolves to time zone',
                        obj=cls,
                        id='timezone.E008',
                    ))
                break
        return errors
