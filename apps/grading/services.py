from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterator, List, Optional, Tuple, Union

from grading.api.yandex_contest import ProblemStatus, YandexContestAPI
from grading.constants import CheckingSystemTypes, YandexCompilers
from grading.models import Checker, CheckingSystem, Submission
from grading.utils import resolve_yandex_contest_problem_alias
from learning.models import AssignmentComment


class CheckerURLError(Exception):
    pass


class CheckerService:
    @staticmethod
    def get_available_compiler_choices(checker: Checker) -> List[str]:
        if 'compilers' not in checker.settings:
            return []
        contest_compilers = checker.settings['compilers']
        return [compiler for compiler in YandexCompilers.choices
                if compiler[0] in contest_compilers]

    @staticmethod
    def resolve_yandex_contest_problem_alias(checker_url: str) -> Tuple[int, str]:
        return resolve_yandex_contest_problem_alias(checker_url)

    @classmethod
    def get_or_create_checker_from_url(cls, checking_system: CheckingSystem, checker_url: str) -> Checker:
        """
        Option commit=False is used to validate URL during assignment form clean
        """
        if checking_system.type != CheckingSystemTypes.YANDEX:
            raise CheckerURLError("Checking system type is not supported")
        try:
            contest_id, problem_alias = cls.resolve_yandex_contest_problem_alias(checker_url)
        except ValueError as e:
            raise CheckerURLError(str(e))
        checker, _ = Checker.objects.get_or_create(
            checking_system=checking_system,
            settings__contest_id=contest_id,
            settings__problem_id=problem_alias,
            defaults={
                'url': checker_url,
                'settings': {
                    'contest_id': contest_id,
                    'problem_id': problem_alias
                }
            }
        )
        return checker


class CheckerSubmissionService:
    @staticmethod
    def update_or_create(solution: AssignmentComment, **settings: Any) -> Submission:
        """
        Creates a new checker submission or updates settings on existing one.
        """
        submission, _ = Submission.objects.update_or_create(
            assignment_submission=solution,
            default={"settings": settings}
        )
        submission.save()
        return submission


@dataclass
class YandexContestProblemResult:
    problem_alias: str
    status: ProblemStatus
    score: Optional[Union[int, Decimal]]
    submission_count: int
    submission_delay: int


@dataclass
class YandexContestParticipantProgress:
    participant_id: int
    yandex_login: str
    score_total: str
    problems: List[YandexContestProblemResult]


def yandex_contest_scoreboard_iterator(client: YandexContestAPI, contest_id: int,
                                       batch_size: Optional[int] = 50) -> Iterator[YandexContestParticipantProgress]:
    paging = {
        "page_size": batch_size,
        "page": 1
    }
    while True:
        status, json_data = client.standings(contest_id, **paging)
        problem_aliases = [t["title"] for t in json_data["titles"]]
        page_total = 0
        for row in json_data['rows']:
            page_total += 1
            problems = []
            for index, data in enumerate(row['problemResults']):
                problem_status = ProblemStatus(data['status'])
                # TODO: how to reuse logic from AssignmentScore?
                if problem_status == ProblemStatus.ACCEPTED:
                    score_str: str = data['score'].replace(',', '.')
                    score = int(round(float(score_str)))
                elif problem_status == ProblemStatus.NOT_ACCEPTED:
                    score = 0
                else:
                    score = None
                problem_result = YandexContestProblemResult(
                    problem_alias=problem_aliases[index],
                    status=problem_status,
                    score=score,
                    submission_count=data['submissionCount'],
                    submission_delay=data['submitDelay'],
                )
                problems.append(problem_result)
            participant_progress = YandexContestParticipantProgress(
                participant_id=row['participantInfo']['id'],
                yandex_login=row['participantInfo']['login'],
                score_total=row['score'],
                problems=problems
            )
            yield participant_progress
        if page_total < paging["page_size"]:
            return
        paging["page"] += 1
