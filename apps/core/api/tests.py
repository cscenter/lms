from rest_framework import serializers

from core.api.fields import CharSeparatedField


def test_char_separated_field_default_separator():
    field = CharSeparatedField()
    assert field.separator == ","


def test_char_separated_field_custom_separator():
    field = CharSeparatedField(separator=".")
    assert field.separator == "."


def test_char_separated_field_to_representation():
    field = CharSeparatedField()
    assert field.to_representation(["a", "b", "c"]) == "a,b,c"


def test_char_separated_field_to_internal_value():
    field = CharSeparatedField()
    assert field.to_internal_value("a,b,c") == ["a", "b", "c"]
