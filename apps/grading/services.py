from typing import Any, List, Tuple

from core.typings import assert_never
from grading.constants import CheckingSystemTypes, YandexCompilers
from grading.models import Checker, CheckingSystem, Submission
from grading.utils import (
    ParsedYandexContestURL, YandexContestScoreSource, parse_yandex_contest_url
)
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
    def parse_yandex_contest_url(checker_url: str) -> ParsedYandexContestURL:
        return parse_yandex_contest_url(checker_url)

    @classmethod
    def get_or_create_checker_from_url(cls, checking_system: CheckingSystem,
                                       checker_url: str) -> Checker:
        supported_types = {CheckingSystemTypes.YANDEX_CONTEST}
        if checking_system.type not in supported_types:
            raise CheckerURLError("Checking system type is not supported")
        if checking_system.type == CheckingSystemTypes.YANDEX_CONTEST:
            try:
                parsed_url = cls.parse_yandex_contest_url(checker_url)
            except ValueError as e:
                raise CheckerURLError(str(e))
            checker_settings = parsed_url.as_dict()
            checker_filters = {"checking_system": checking_system}
            for key, value in checker_settings.items():
                checker_filters[f"settings__{key}"] = value
            checker, _ = Checker.objects.get_or_create(
                defaults={
                    'url': checker_url,
                    'settings': checker_settings
                },
                **checker_filters
            )
            return checker
        else:
            assert_never(checking_system.type)


class CheckerSubmissionService:
    @staticmethod
    def update_or_create(solution: AssignmentComment, **settings: Any) -> Submission:
        """
        Creates a new checker submission or updates settings on existing one.
        """
        submission, _ = Submission.objects.update_or_create(
            assignment_submission=solution,
            defaults={"settings": settings}
        )
        submission.save()
        return submission
