from django.db.models.signals import post_save
from django.dispatch import receiver

from contests.models import Submission, SubmissionStatus
from contests.tasks import add_new_submission_to_checking_system
from courses.models import AssignmentSubmissionFormats


@receiver(post_save, sender=Submission)
def add_submission_to_checking_system(sender, instance: Submission,
                                      created, update_fields, *args, **kwargs):
    if created:
        add_new_submission_to_checking_system.delay(submission_id=instance.pk,
                                                    retries=3)
    elif update_fields and 'status' in update_fields:
        if instance.status == SubmissionStatus.PASSED:
            assignment_comment = instance.assignment_comment
            submission_type = assignment_comment.student_assignment.assignment.submission_type
            if submission_type == AssignmentSubmissionFormats.CODE_REVIEW:
                from code_reviews.tasks import upload_attachment_to_gerrit
                upload_attachment_to_gerrit.delay(assignment_comment.pk)
