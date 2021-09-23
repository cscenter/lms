from typing import Any, List, Tuple

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
            defaults={"settings": settings}
        )
        submission.save()
        return submission
