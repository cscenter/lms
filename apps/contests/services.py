from contests.models import Submission


class SubmissionService:
    @staticmethod
    def save_submission_settings(assignment_submission, **kwargs):
        """
        Creates a Submission with all kwargs (e.g., compiler) saved as settings.
        """
        submission, _ = Submission.objects.get_or_create(
            assignment_comment=assignment_submission,
            settings=kwargs
        )
        submission.save()
