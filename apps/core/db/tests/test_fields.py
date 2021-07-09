import pytest
import pytz

from django.core.exceptions import ValidationError

from core.db.fields import TimeZoneField


@pytest.mark.django_db
def test_timezone_field_deconstruct():
    x = TimeZoneField()
    name, path, args, kwargs = x.deconstruct()
    assert 'choices' not in kwargs
    new_instance = TimeZoneField(*args, **kwargs)
    assert x._default_choices == new_instance._default_choices
    x = TimeZoneField(choices=[('Europe/Moscow', 'Europe/Moscow2')])
    name, path, args, kwargs = x.deconstruct()
    assert 'choices' in kwargs


@pytest.mark.django_db
def test_timezone_field_choices():
    x = TimeZoneField()
    assert {tz for tz, _ in x.choices} == pytz.common_timezones_set
    x = TimeZoneField(choices=[('Europe/Moscow', 'Europe/Moscow2')])
    # TODO: django-stubs defines Field.choices as Iterable[...], fix that.
    assert len(x.choices) == 1  # type: ignore[arg-type]
    assert x.choices[0][0] == 'Europe/Moscow'  # type: ignore[index]
    x = TimeZoneField(name='x', choices=[('foo', 'Europe/Moscow2')])
    errors = x.check()
    assert len(errors) == 1
    assert errors[0].id == 'fields.E201'


@pytest.mark.django_db
def test_timezone_field_to_python():
    tz = pytz.timezone('Europe/Moscow')
    x = TimeZoneField()
    assert x.to_python('Europe/Moscow') == tz
    with pytest.raises(ValidationError):
        _ = x.to_python('Europe/Moscow2')  # invalid tz id
    assert x.to_python('') is None


@pytest.mark.django_db
def test_timezone_field_get_prep_value():
    x = TimeZoneField()
    tz = pytz.timezone('Europe/Moscow')
    assert x.get_prep_value(tz) == str(tz)
    assert x.get_prep_value('Europe/Moscow') == str(tz)
