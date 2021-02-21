import pytest

from grading.constants import CheckingSystemTypes
from grading.models import Checker
from grading.services import CheckerService, CheckerURLError
from grading.tests.factories import CheckerFactory, CheckingSystemFactory
from grading.utils import get_yandex_contest_problem_url


def get_compilers(checker):
    return [compiler[0] for compiler
            in CheckerService.get_available_compiler_choices(checker)]


@pytest.mark.django_db
def test_get_available_compiler_choices():
    checker = CheckerFactory()
    assert not get_compilers(checker)
    checker.settings['compilers'] = ['ruby']
    checker.save()
    assert 'rust' not in get_compilers(checker)
    assert 'ruby' in get_compilers(checker)


@pytest.mark.django_db
def test_get_or_create_checker_from_url_no_commit():
    checking_system = CheckingSystemFactory(type=CheckingSystemTypes.YANDEX)
    checking_system_url = get_yandex_contest_problem_url(15, 'A')
    CheckerService.get_or_create_checker_from_url(checking_system,
                                                  checking_system_url,
                                                  commit=False)
    assert Checker.objects.count() == 0


@pytest.mark.django_db
def test_get_or_create_checker_from_url_throws_error_on_bad_url():
    checking_system = CheckingSystemFactory(type=CheckingSystemTypes.YANDEX)
    checking_system_url = get_yandex_contest_problem_url(0, 'A')
    with pytest.raises(CheckerURLError) as e:
        CheckerService.get_or_create_checker_from_url(checking_system,
                                                      checking_system_url,
                                                      commit=False)
    assert 'Contest ID should be positive' in str(e.value)


@pytest.mark.django_db
def test_get_or_create_checker_from_url_commit_true():
    checking_system = CheckingSystemFactory(type=CheckingSystemTypes.YANDEX)
    checking_system_url = get_yandex_contest_problem_url(15, 'D')
    checker = CheckerService.get_or_create_checker_from_url(checking_system,
                                                            checking_system_url)
    assert checker.checking_system.type == CheckingSystemTypes.YANDEX
    assert checker.url == checking_system_url
    assert checker.settings['contest_id'] == 15
    assert checker.settings['problem_id'] == 'D'
