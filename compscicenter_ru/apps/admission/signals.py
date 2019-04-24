# -*- coding: utf-8 -*-
import datetime

from django.db.models.signals import post_save, m2m_changed, post_delete
from django.dispatch import receiver
from post_office.models import Email
from post_office.utils import get_email_template

from admission.models import Applicant, Interview, Comment, Campaign, \
    InterviewStream, InterviewSlot
from admission.utils import slot_range, \
    generate_interview_feedback_email

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
    interview = instance
    __sync_applicant_status(interview)
    if interview.status in [Interview.CANCELED, Interview.DEFERRED]:
        interview.delete_reminder()
        interview.delete_feedback()
    elif interview.status == Interview.COMPLETED:
        generate_interview_feedback_email(interview)


# TODO: add tests
@receiver(post_delete, sender=Interview)
def post_delete_interview(sender, instance, *args, **kwargs):
    interview = instance
    applicant = interview.applicant
    Applicant.objects.filter(pk=applicant.pk).update(
        status=Applicant.INTERVIEW_TOBE_SCHEDULED)
    interview.delete_reminder()
    interview.delete_feedback()


# FIXME: Doesn't work through admin interface, what about tests on public?
@receiver(m2m_changed, sender=Interview.interviewers.through)
def interview_interviewers_m2m_changed(sender, instance, action, *args, **kwargs):
    """
    We are struggling with two cases:
        * We only remove some interviewers
        * We remove and add some interviewers. In that case `post_remove`
        will be called first, then `post_add`
    """
    if action == "post_remove":
        __sync_applicant_status(instance, check_comments=True)
        instance.__post_remove_called_before = True
        instance.__status_was_changed_by_sync_method_call = True
    elif action == "post_add":
        # Previous `post_remove` call could accidentally update interview and
        # applicant status to `complete` state. Fix this if need.
        # FIXME: Кажется, что нужно проверять 2 вещи - что-то было удалено и статус изменился со времени вызова `post_remove`, т.е. он был неверно подкорректирован.
        # TODO: add test
        pass


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
    __sync_applicant_status(interview, check_comments=True)
    if interview.status == Interview.COMPLETED:
        generate_interview_feedback_email(interview)
    if comment.interviewer not in interviewers and comment.interviewer.is_curator:
        interview.interviewers.add(comment.interviewer)


def __sync_applicant_status(interview, check_comments=False):
    """Keep in sync interview and applicant statuses."""
    if interview.applicant.status in APPLICANT_FINAL_STATES:
        return
    new_status = object()
    if interview.status in [Interview.APPROVAL, Interview.APPROVED]:
        if check_comments and len(
                interview.interviewers.all()) == interview.comments.count():
            interview.status = Interview.COMPLETED
            Interview.objects.filter(pk=interview.pk).update(
                status=interview.status)
            new_status = Applicant.INTERVIEW_COMPLETED
        else:
            new_status = Applicant.INTERVIEW_SCHEDULED
    elif interview.status in [Interview.CANCELED, Interview.DEFERRED]:
        new_status = Applicant.INTERVIEW_TOBE_SCHEDULED
    elif interview.status == Interview.COMPLETED:
        new_status = Applicant.INTERVIEW_COMPLETED
    else:
        raise ValueError("Unknown interview status")
    if interview.applicant.status != new_status:
        interview.applicant.status = new_status
        Applicant.objects.filter(pk=interview.applicant.pk).update(
            status=interview.applicant.status)


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
