import re

from django.utils.translation import gettext_lazy as _

YANDEX_CONTEST_DOMAIN = "contest.yandex.ru"
YANDEX_CONTEST_PROBLEM_URL = r"/contest\/(?P<contest_id>[\d]+)\/problems\/(?P<problem_id>[a-zA-Z0-9]?)(?P<trailing_slash>[\/]?)"
YANDEX_CONTEST_PROBLEM_REGEX = re.compile(YANDEX_CONTEST_PROBLEM_URL)


def resolve_problem_id(url):
    prefix, domain, suffix = url.partition(YANDEX_CONTEST_DOMAIN)
    if not domain:
        raise ValueError(_("Not a Yandex.Contest URL"))
    match = YANDEX_CONTEST_PROBLEM_REGEX.fullmatch(suffix)
    if not match:
        raise ValueError(_("Cannot extract contest and problem ids from URL"))
    contest_id = int(match.group('contest_id'))
    if contest_id == 0:
        raise ValueError(_("Contest ID should be positive"))
    problem_id = match.group('problem_id')
    if not problem_id:
        raise ValueError(_("URL does not contain ID of the problem"))
    return contest_id, problem_id
