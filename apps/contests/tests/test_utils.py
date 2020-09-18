import pytest

from contests.utils import resolve_problem_id


def test_resolve_problem_id_should_fail_for_wrong_domain():
    with pytest.raises(ValueError) as e:
        resolve_problem_id('https://www.yandex.ru')
    assert 'Not a Yandex.Contest URL' in str(e.value)


def test_resolve_problem_id_should_fail_for_bad_syntax():
    with pytest.raises(ValueError) as e:
        resolve_problem_id('https://contest.yandex.ru/aaa/1/bbb/2/')
    assert 'Cannot extract contest and problem ids from URL' in str(e.value)


def test_resolve_problem_id_should_fail_on_bad_contest_id():
    with pytest.raises(ValueError) as e:
        resolve_problem_id("https://contest.yandex.ru/contest/0000/problems/A/")
    assert 'Contest ID should be positive' in str(e.value)


def test_resolve_problem_id_should_fail_when_no_problem_id():
    with pytest.raises(ValueError) as e:
        resolve_problem_id("https://contest.yandex.ru/contest/15/problems/")
    assert 'URL does not contain ID of the problem' in str(e.value)


def test_resolve_problem_id_should_resolve_valid_links():
    problem_url = "https://contest.yandex.ru/contest/15/problems/D/"
    contest_id, problem_id = resolve_problem_id(problem_url)
    assert contest_id == 15
    assert problem_id == 'D'
