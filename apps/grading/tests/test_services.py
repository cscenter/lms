import pytest

from grading.constants import CheckingSystemTypes
from grading.services import CheckerService, CheckerURLError
from grading.tests.factories import CheckerFactory, CheckingSystemFactory
from grading.utils import YandexContestScoreSource, get_yandex_contest_url


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
def test_get_or_create_checker_from_url_throws_invalid_url():
    checking_system = CheckingSystemFactory(type=CheckingSystemTypes.YANDEX)
    checking_system_url = get_yandex_contest_url(0, 'A')
    with pytest.raises(CheckerURLError) as e:
        CheckerService.get_or_create_checker_from_url(checking_system,
                                                      checking_system_url)
    assert 'Contest ID should be positive' in str(e.value)


@pytest.mark.django_db
def test_get_or_create_checker_from_url_valid_problem_url():
    checking_system = CheckingSystemFactory(type=CheckingSystemTypes.YANDEX)
    checking_system_url = get_yandex_contest_url(15, 'D')
    checker = CheckerService.get_or_create_checker_from_url(checking_system,
                                                            checking_system_url)
    assert checker.checking_system.type == CheckingSystemTypes.YANDEX
    assert checker.url == checking_system_url
    assert checker.settings['score_input'] == YandexContestScoreSource.PROBLEM.value
    assert checker.settings['contest_id'] == 15
    assert checker.settings['problem_id'] == 'D'


@pytest.mark.django_db
def test_get_or_create_checker_from_url_valid_contest_url():
    checking_system = CheckingSystemFactory(type=CheckingSystemTypes.YANDEX)
    checking_system_url = get_yandex_contest_url(15, problem_id=None)
    checker = CheckerService.get_or_create_checker_from_url(checking_system,
                                                            checking_system_url)
    assert checker.checking_system.type == CheckingSystemTypes.YANDEX
    assert checker.url == checking_system_url
    assert checker.settings['score_input'] == YandexContestScoreSource.CONTEST.value
    assert checker.settings['contest_id'] == 15
    assert 'problem_id' not in checker.settings
