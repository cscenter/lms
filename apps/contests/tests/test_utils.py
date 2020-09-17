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


@pytest.mark.parametrize("url,expected_contest_id,expected_problem_id",
                         [("https://contest.yandex.ru/contest/15/problems/", 15, ''),
                          ("https://contest.yandex.ru/contest/15/problems/D/", 15, 'D')])
def test_resolve_problem_id_should_resolve_valid_links(url, expected_contest_id,
                                                       expected_problem_id):
    contest_id, problem_id = resolve_problem_id(url)
    assert contest_id == expected_contest_id
    assert problem_id == expected_problem_id
