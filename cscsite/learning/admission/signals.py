# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now

from learning.admission.models import Applicant, Interview, Comment, Campaign


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
    APPLICANT_FINAL_STATES = (Applicant.ACCEPT,
                              Applicant.VOLUNTEER,
                              Applicant.ACCEPT_IF,
                              Applicant.REJECTED_BY_INTERVIEW,
                              Applicant.THEY_REFUSED)
    today_start = datetime.datetime.combine(now(), datetime.time.min)
    # Set applicant status to `INTERVIEW_SCHEDULED` if interview has been
    # created with active status and current applicant status not in final state
    if created and interview.status in [Interview.APPROVAL, Interview.WAITING]:
        if interview.applicant.status not in APPLICANT_FINAL_STATES:
            interview.applicant.status = Applicant.INTERVIEW_SCHEDULED
    elif interview.status in [Interview.CANCELED, Interview.DEFERRED]:
        # When trying to deactivate interview, check that applicant hasn't
        # other active or completed interviews, if so,
        # revert applicant status to `INTERVIEW_TOBE_SCHEDULED`
        has_positive_interviews = (
            Interview.objects
            .filter(applicant=interview.applicant,
                    date__gte=today_start)
            .exclude(status__in=[Interview.CANCELED, Interview.DEFERRED])
            .count()
        ) > 0
        if not has_positive_interviews:
            interview.applicant.status = Applicant.INTERVIEW_TOBE_SCHEDULED
    interview.applicant.save()


@receiver(post_save, sender=Comment)
def post_save_interview_comment(sender, instance, created,
                                *args, **kwargs):
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
    comments_cnt = Comment.objects.filter(interview=interview).count()
    if len(interviewers) == comments_cnt:
        interview.status = Interview.COMPLETED
        interview.save()
        interview.applicant.status = Applicant.INTERVIEW_COMPLETED
        interview.applicant.save()
    if comment.interviewer not in interviewers and comment.interviewer.is_curator:
        interview.interviewers.add(comment.interviewer)
