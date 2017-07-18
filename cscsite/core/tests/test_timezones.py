import pytest


def test_settings(settings):
    assert settings.TIME_ZONE == 'UTC'
