# -*- coding: utf-8 -*-
import datetime

from django.db.models.signals import post_save
from django.dispatch import receiver

from learning.admission.models import Applicant, Interview, Comment, Campaign, \
    InterviewStream, InterviewSlot
from learning.admission.utils import slot_range

APPLICANT_FINAL_STATES = (Applicant.ACCEPT,
                          Applicant.VOLUNTEER,
                          Applicant.ACCEPT_IF,
                          Applicant.REJECTED_BY_INTERVIEW,
                          Applicant.THEY_REFUSED)


@receiver(post_save, sender=Campaign)
def post_save_campaign(sender, instance, created, *args, **kwargs):
    """Make sure we have only one active campaign for a city in a moment."""
    campaign = instance
    # OK to update on each model change
    if campaign.current:
        (Campaign.objects
         .filter(city=campaign.city)
         .exclude(pk=campaign.pk)
         .update(current=False))


@receiver(post_save, sender=Interview)
def post_save_interview(sender, instance, created, *args, **kwargs):
    """Set appropriate applicant status based on interview status."""
    interview = instance
    applicant_status_updated = False
    # Set applicant status to `INTERVIEW_SCHEDULED` if interview has been
    # created with active status and current applicant status not in final state
    if created and interview.status in [Interview.APPROVAL, Interview.APPROVED]:
        if interview.applicant.status not in APPLICANT_FINAL_STATES:
            interview.applicant.status = Applicant.INTERVIEW_SCHEDULED
    elif interview.status in [Interview.CANCELED, Interview.DEFERRED]:
        interview.applicant.status = Applicant.INTERVIEW_TOBE_SCHEDULED
    else:
        applicant_status_updated = __check_interview_status(interview)
    if not applicant_status_updated:
        (Applicant.objects
         .filter(pk=interview.applicant_id)
         .update(status=interview.applicant.status))


@receiver(post_save, sender=Comment)
def post_save_interview_comment(sender, instance, created, *args, **kwargs):
    """
    Set interview and applicant status to `completed` if all interviewers
    leave a comment.
    Add curator to interviewers if he leave a comment and not in a list yet.
    """
    if not created:
        return
    comment = instance
    interview = comment.interview
    interviewers = interview.interviewers.all()
    __check_interview_status(interview)
    if comment.interviewer not in interviewers and comment.interviewer.is_curator:
        interview.interviewers.add(comment.interviewer)


def __check_interview_status(interview):
    """
    Try to sync interview and applicant statuses when `complete`
    state is reachable.
    """
    update_applicant_status = False
    if interview.status == Interview.APPROVED:
        if len(interview.interviewers.all()) == interview.comments.count():
            interview.status = Interview.COMPLETED
            (Interview.objects
             .filter(pk=interview.pk)
             .update(status=interview.status))
            update_applicant_status = True
    elif interview.status == Interview.COMPLETED:
        update_applicant_status = True
    if (update_applicant_status and
            interview.applicant.status not in APPLICANT_FINAL_STATES):
        interview.applicant.status = Applicant.INTERVIEW_COMPLETED
        rows = (Applicant.objects
                .filter(pk=interview.applicant.pk)
                .update(status=interview.applicant.status))
        return rows > 0
    return False


@receiver(post_save, sender=InterviewStream)
def post_save_interview_stream(sender, instance, created, *args, **kwargs):
    """
    Generate slots from stream. Stream should be created with admin interface,
    which using atomic internal, don't worry about consistency in that case
    """
    if created:
        interview_stream = instance
        step = datetime.timedelta(minutes=interview_stream.duration)
        srange = slot_range(interview_stream.start_at,
                            interview_stream.end_at, step)
        InterviewSlot.objects.bulk_create([
            InterviewSlot(start_at=start, end_at=end,
                          stream=interview_stream) for start, end in srange])
