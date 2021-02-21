from django.utils.translation import gettext_lazy as _

from grading.api.yandex_contest import YANDEX_CONTEST_DOMAIN, \
    YANDEX_CONTEST_PROBLEM_REGEX, YANDEX_CONTEST_PROBLEM_URL


def get_yandex_contest_problem_url(contest_id, problem_id):
    return YANDEX_CONTEST_PROBLEM_URL.format(contest_id=contest_id,
                                             problem_id=problem_id)

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
