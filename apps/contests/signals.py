from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from contests.models import Submission
from contests.constants import SubmissionStatus, CheckingSystemTypes
from contests.tasks import add_new_submission_to_checking_system, \
    retrieve_yandex_contest_checker_compilers
from courses.models import AssignmentSubmissionFormats, Assignment


@receiver(pre_save, sender=Assignment)
def retrieve_yandex_contest_compilers(sender, instance: Assignment,
                                      *args, **kwargs):
    """
    Triggered on every save for assigments with checker to allow updating
    compiler list on demand by clicking "Save" button on assignment form.
    """
    if instance.checker:
        if instance.checker.checking_system.type == CheckingSystemTypes.YANDEX:
            retrieve_yandex_contest_checker_compilers.delay(
                checker_id=instance.checker.pk, retries=3
            )


@receiver(post_save, sender=Submission)
def add_submission_to_checking_system(sender, instance: Submission,
                                      created, update_fields, *args, **kwargs):
    if created:
        add_new_submission_to_checking_system.delay(submission_id=instance.pk,
                                                    retries=3)
    elif update_fields and 'status' in update_fields:
        if instance.status == SubmissionStatus.PASSED:
            assignment_submission = instance.assignment_submission
            submission_type = assignment_submission.student_assignment.assignment.submission_type
            if submission_type == AssignmentSubmissionFormats.CODE_REVIEW:
                from code_reviews.tasks import upload_attachment_to_gerrit
                upload_attachment_to_gerrit.delay(assignment_submission.pk)
