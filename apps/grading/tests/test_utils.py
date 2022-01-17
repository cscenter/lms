import pytest

from grading.utils import parse_yandex_contest_url


def test_parse_yandex_contest_url_should_fail_for_wrong_domain():
    with pytest.raises(ValueError) as e:
        parse_yandex_contest_url('https://www.yandex.ru')
    assert 'Not a Yandex.Contest URL' in str(e.value)


def test_parse_yandex_contest_url_should_fail_for_bad_syntax():
    with pytest.raises(ValueError) as e:
        parse_yandex_contest_url('https://contest.yandex.ru/aaa/1/bbb/2/')
    assert 'Wrong Yandex.Contest URL format' in str(e.value)
    with pytest.raises(ValueError) as e:
        parse_yandex_contest_url('https://contest.yandex.ru/aaa/1/')
    assert 'Wrong Yandex.Contest URL format' in str(e.value)


def test_parse_yandex_contest_url_should_fail_on_bad_contest_id():
    with pytest.raises(ValueError) as e:
        parse_yandex_contest_url("https://contest.yandex.ru/contest/0000/problems/A/")
    assert 'Contest ID should be positive' in str(e.value)
    with pytest.raises(ValueError) as e:
        parse_yandex_contest_url("https://contest.yandex.ru/contest/0000/")
    assert 'Contest ID should be positive' in str(e.value)


def test_parse_yandex_contest_url_should_fail_when_no_problem_alias():
    with pytest.raises(ValueError) as e:
        parse_yandex_contest_url("https://contest.yandex.ru/contest/15/problems/")
    assert 'URL does not contain ID of the problem' in str(e.value)


def test_parse_yandex_contest_url_should_resolve_valid_links():
    problem_url = "https://contest.yandex.ru/contest/15/problems/D/"
    parsed_url = parse_yandex_contest_url(problem_url)
    assert parsed_url.contest_id == 15
    assert parsed_url.problem_alias == 'D'
    # Problem IDs can be unusual
    problem_url = "https://contest.yandex.ru/contest/15/problems/1A/"
    parsed_url = parse_yandex_contest_url(problem_url)
    assert parsed_url.contest_id == 15
    assert parsed_url.problem_alias == '1A'
    # Link to the whole contest
    problem_url = "https://contest.yandex.ru/contest/15/"
    parsed_url = parse_yandex_contest_url(problem_url)
    assert parsed_url.contest_id == 15
    assert parsed_url.problem_alias is None
    # Without trailing slash
    parsed_url = parse_yandex_contest_url("https://contest.yandex.ru/contest/14")
    assert parsed_url.contest_id == 14
    assert parsed_url.problem_alias is None
