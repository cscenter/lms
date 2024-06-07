from django.db.models.signals import post_delete, post_save, pre_delete
from django.dispatch import receiver

from admission.constants import InterviewSections
from admission.models import Applicant, Campaign, Comment, Interview, InterviewSlot
from admission.services import EmailQueueService

APPLICANT_FINAL_STATES = (
    Applicant.ACCEPT,
    Applicant.ACCEPT_IF,
    Applicant.REJECTED_BY_INTERVIEW,
    Applicant.THEY_REFUSED,
)


@receiver(post_save, sender=Campaign)
def post_save_campaign(sender, instance, created, *args, **kwargs):
    """Make sure we have only one active campaign for a branch"""
    campaign = instance
    if campaign.current:
        (
            Campaign.objects.filter(branch=campaign.branch)
            .exclude(pk=campaign.pk)
            .update(current=False)
        )


@receiver(post_save, sender=Interview)
def post_save_interview(sender, instance, created, *args, **kwargs):
    interview = instance
    if interview.status in [Interview.CANCELED, Interview.DEFERRED]:
        EmailQueueService.remove_interview_reminder(interview)
        EmailQueueService.remove_interview_feedback_emails(interview)
    elif interview.status == Interview.COMPLETED:
        EmailQueueService.generate_interview_feedback_email(interview)




# TODO: add tests
@receiver(pre_delete, sender=Interview)
def pre_delete_interview(sender, instance, *args, **kwargs):
    interview = instance
    EmailQueueService.remove_interview_reminder(interview)
    EmailQueueService.remove_interview_feedback_emails(interview)


@receiver(post_save, sender=Comment)
def post_save_interview_comment(sender, instance, created, *args, **kwargs):
    if not created:
        return
    comment = instance
    interview = comment.interview
    interviewers = list(interview.interviewers.all())
    # Adds curator to interviewers if they leave a comment
    # but not in a list of interviewers.
    is_assigned_interviewer = comment.interviewer not in interviewers
    if is_assigned_interviewer and comment.interviewer.is_curator:
        interview.interviewers.add(comment.interviewer)
    # If all interviewers have left comments mark interview as completed
    comment_authors = {c.interviewer_id for c in interview.comments.all()}
    if set(i.pk for i in interviewers).issubset(comment_authors):
        interview.status = Interview.COMPLETED
        interview.save(update_fields=["status"])


@receiver(post_save, sender=InterviewSlot)
def post_save_interview_slot(sender, instance, created, *args, **kwargs):
    if created:
        instance.stream.compute_fields("slots_count")
    instance.stream.compute_fields("slots_occupied_count")


@receiver(post_delete, sender=InterviewSlot)
def post_delete_interview_slot(sender, instance, *args, **kwargs):
    instance.stream.compute_fields("slots_count")
    instance.stream.compute_fields("slots_occupied_count")
