from grading.constants import YandexCompilers, CheckingSystemTypes
from grading.models import Submission, Checker
from grading.utils import resolve_problem_id


class CheckerURLError(Exception):
    pass


class CheckerService:
    @staticmethod
    def get_available_compiler_choices(checker):
        if 'compilers' not in checker.settings:
            return []
        contest_compilers = checker.settings['compilers']
        return [compiler for compiler in YandexCompilers.choices
                if compiler[0] in contest_compilers]

    @staticmethod
    def get_or_create_checker_from_url(checking_system, checker_url,
                                       commit=True):
        """
        Option commit=False is used to validate URL during assignment form clean
        """
        if checking_system.type == CheckingSystemTypes.YANDEX:
            try:
                contest_id, problem_id = resolve_problem_id(checker_url)
            except ValueError as e:
                raise CheckerURLError(str(e))
            if commit:
                checker, _ = Checker.objects.get_or_create(
                    checking_system=checking_system,
                    settings__contest_id=contest_id,
                    settings__problem_id=problem_id, defaults={
                        'url': checker_url,
                        'settings': {'contest_id': contest_id,
                                     'problem_id': problem_id}
                    }
                )
                return checker
        else:
            raise CheckerURLError("Checking system type is not supported")


class SubmissionService:
    @staticmethod
    def update_or_create_submission_settings(assignment_submission, **kwargs):
        """
        Updates or creates a Submission with all kwargs (e.g., compiler)
        saved as settings.
        """
        submission, _ = Submission.objects.update_or_create(
            assignment_submission=assignment_submission,
            settings=kwargs
        )
        submission.save()
