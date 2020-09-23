import pytest

from contests.services import CheckerService
from contests.tests.factories import CheckerFactory


def get_compilers(checker):
    return [compiler[0] for compiler
            in CheckerService.get_available_compiler_choices(checker)]


@pytest.mark.django_db
def test_get_available_compiler_choices():
    checker = CheckerFactory()
    assert 'rust' in get_compilers(checker)
    checker.settings['compilers'] = ['ruby']
    checker.save()
    assert 'rust' not in get_compilers(checker)
    assert 'ruby' in get_compilers(checker)
