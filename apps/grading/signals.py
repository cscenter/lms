from functools import partial

from django.apps import apps
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from courses.constants import AssignmentFormat
from courses.models import Assignment
from grading.constants import CheckingSystemTypes, SubmissionStatus
from grading.models import Submission
from grading.tasks import (
    add_new_submission_to_checking_system,
    update_checker_yandex_contest_problem_compilers
)
from grading.utils import YandexContestScoreSource


@receiver(post_save, sender=Assignment)
def retrieve_yandex_contest_problem_compilers(sender, instance: Assignment,
                                              *args, **kwargs):
    """
    Triggered on every save for assigment with checker to allow updating
    compiler list on demand by clicking "Save" button on assignment form.
    """
    checker = instance.checker
    if not (checker and checker.checking_system.type == CheckingSystemTypes.YANDEX_CONTEST):
        return
    if checker.settings.get('score_input') != YandexContestScoreSource.PROBLEM.value:
        return
    fetch_compilers = partial(update_checker_yandex_contest_problem_compilers.delay,
                              checker_id=checker.pk, retries=3)
    transaction.on_commit(fetch_compilers)


@receiver(post_save, sender=Submission)
def add_submission_to_checking_system(sender, instance: Submission,
                                      created, update_fields, *args, **kwargs):
    if created:
        check_func = partial(add_new_submission_to_checking_system.delay,
                             submission_id=instance.pk, retries=3)
        transaction.on_commit(check_func)
    if apps.is_installed("code_reviews"):
        from code_reviews.gerrit.tasks import upload_attachment_to_gerrit

        # FIXME: use service method or FieldTracker instead
        if update_fields and 'status' in update_fields:
            if instance.status == SubmissionStatus.PASSED:
                assignment_submission = instance.assignment_submission
                submission_type = assignment_submission.student_assignment.assignment.submission_type
                if submission_type == AssignmentFormat.CODE_REVIEW:
                    upload_func = partial(upload_attachment_to_gerrit.delay,
                                          assignment_submission.pk)
                    transaction.on_commit(upload_func)
