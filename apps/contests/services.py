from contests.constants import YandexCompilers
from contests.models import Submission


class CheckerService:
    @staticmethod
    def get_available_compiler_choices(checker):
        """
        Returns a list of compilers for the checker, fallback to YandexCompilers
        """
        if 'compilers' not in checker.settings:
            return YandexCompilers.choices
        contest_compilers = checker.settings['compilers']
        return [compiler for compiler in YandexCompilers.choices
                if compiler[0] in contest_compilers]


class SubmissionService:
    @staticmethod
    def save_submission_settings(assignment_submission, **kwargs):
        """
        Creates a Submission with all kwargs (e.g., compiler) saved as settings.
        """
        submission, _ = Submission.objects.get_or_create(
            assignment_submission=assignment_submission,
            settings=kwargs
        )
        submission.save()
