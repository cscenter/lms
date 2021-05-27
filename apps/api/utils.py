import copy
import hashlib
from functools import wraps
from typing import Iterable, Type
from urllib.parse import quote

from rest_framework import serializers

from django.utils.encoding import force_bytes

API_FRAGMENT_KEY_TEMPLATE = 'api.cache.%s.%s'


def make_api_fragment_key(fragment_name, vary_on=None):
    if vary_on is None:
        vary_on = ()
    key = ':'.join(quote(var) for var in vary_on)
    args = hashlib.md5(force_bytes(key))
    return API_FRAGMENT_KEY_TEMPLATE % (fragment_name, args.hexdigest())


# TODO: add test
def requires_context(f):
    """
    The decorator provides .requires_context=True for the callable function
    sets the default value of the serializer field.
    """
    @wraps(f)
    def wrapper(serializer_field):
        return f(serializer_field)
    wrapper.requires_context = True
    return wrapper


class DynamicFieldsModelSerializer(serializers.ModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument
    that controls which fields should be displayed
    """

    def __init__(self, *args, **kwargs):
        fields: Iterable[str] = kwargs.pop('fields', None)
        super().__init__(*args, **kwargs)

        if fields is not None:
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in allowed:
                if field_name not in existing:
                    raise ValueError(f"Field with name '{field_name}' "
                                     f"is not defined in {self.__class__.__name__}")
            # Drop any fields that are not specified in the `fields` argument
            for field_name in existing - allowed:
                self.fields.pop(field_name)


def create_serializer_class(name, fields):
    return type(name, (serializers.Serializer, ), fields)


def inline_serializer(*, fields, data=None, **kwargs):
    serializer_class = create_serializer_class(name='', fields=fields)

    if data is not None:
        return serializer_class(data=data, **kwargs)

    return serializer_class(**kwargs)


def get_serializer_fields(serializer: Type[serializers.Serializer], fields: Iterable[str]):
    """
    Returns subset of serializer fields. Useful with *inline_serializer*.

    Note:
        Reuse serializers as little as possible.
    """
    return {field_name: copy.deepcopy(field_instance) for field_name, field_instance
            in serializer().get_fields().items() if field_name in fields}
