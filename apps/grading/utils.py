import dataclasses
from enum import Enum
from typing import Any, Dict, Literal, Optional, Tuple

from django.utils.translation import gettext_lazy as _

from grading.api.yandex_contest import (
    YANDEX_CONTEST_DOMAIN, YANDEX_CONTEST_PROBLEM_REGEX, YANDEX_CONTEST_PROBLEM_URL,
    YANDEX_CONTEST_REGEX, YANDEX_CONTEST_URL
)


def get_yandex_contest_url(contest_id: int,
                           problem_id: Optional[str] = None) -> str:
    if problem_id is None:
        return YANDEX_CONTEST_URL.format(contest_id=contest_id)
    return YANDEX_CONTEST_PROBLEM_URL.format(contest_id=contest_id,
                                             problem_id=problem_id)


class YandexContestScoreSource(Enum):
    CONTEST = 'contest'
    PROBLEM = 'problem'


@dataclasses.dataclass
class ParsedYandexContestURL:
    type: YandexContestScoreSource
    contest_id: int
    problem_alias: Optional[str]

    def as_dict(self) -> Dict[str, Any]:
        data = {
            "score_input": self.type.value,
            "contest_id": self.contest_id,
        }
        if self.type == YandexContestScoreSource.PROBLEM:
            data["problem_id"] = self.problem_alias
        return data


def parse_yandex_contest_url(url: str) -> ParsedYandexContestURL:
    """
    Extracts contest id, [problem alias] from yandex contest url.

    Supported formats:
        https://contest.yandex.ru/contest/{contest_id}/
        https://contest.yandex.ru/contest/{contest_id}/problems/{problem_id}
    """
    prefix, domain, suffix = url.partition(YANDEX_CONTEST_DOMAIN)
    if not domain:
        raise ValueError(_("Not a Yandex.Contest URL"))
    match = YANDEX_CONTEST_PROBLEM_REGEX.fullmatch(suffix)
    if not match:
        match = YANDEX_CONTEST_REGEX.fullmatch(suffix)
        if not match:
            raise ValueError(_("Wrong Yandex.Contest URL format"))
        url_type = YandexContestScoreSource.CONTEST
    else:
        url_type = YandexContestScoreSource.PROBLEM
    contest_id = int(match.group('contest_id'))
    if contest_id == 0:
        raise ValueError(_("Contest ID should be positive"))
    if url_type == YandexContestScoreSource.PROBLEM:
        problem_alias = match.group('problem_alias')
        if not problem_alias:
            raise ValueError(_("URL does not contain ID of the problem"))
        return ParsedYandexContestURL(type=url_type, contest_id=contest_id,
                                      problem_alias=problem_alias)
    elif url_type == YandexContestScoreSource.CONTEST:
        return ParsedYandexContestURL(type=url_type, contest_id=contest_id,
                                      problem_alias=None)
