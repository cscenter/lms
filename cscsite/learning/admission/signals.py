# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime
from django.apps import apps
from django.utils.timezone import now


def post_save_interview(sender, instance, created,
                        *args, **kwargs):
    """Set appropriate applicant status based on interview status."""
    Applicant = apps.get_model('admission', 'Applicant')
    Interview = apps.get_model('admission', 'Interview')
    interview = instance
    # FIXME: move to constants?
    APPLICANT_FINAL_STATUSES = (Applicant.ACCEPT,
                                Applicant.VOLUNTEER,
                                Applicant.ACCEPT_IF,
                                Applicant.REJECTED_BY_INTERVIEW,
                                Applicant.THEY_REFUSED)
    today_start = datetime.datetime.combine(now(), datetime.time.min)
    # Set applicant status to `INTERVIEW_SCHEDULED` if interview created
    # with active status and current applicant status not in final state
    if created and interview.status in [Interview.APPROVAL, Interview.WAITING]:
        if interview.applicant.status not in APPLICANT_FINAL_STATUSES:
            interview.applicant.status = Applicant.INTERVIEW_SCHEDULED
    elif interview.status in [Interview.CANCELED, Interview.DEFERRED]:
        # If we deactivate interview and no active or completed interviews for
        # applicant, revert applicant status to `INTERVIEW_TOBE_SCHEDULED`
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


def post_save_interview_comment(sender, instance, created,
                                *args, **kwargs):
    """
    Set interview and applicant status to `completed` if all interviewers
    leave a comment.
    Add curator to interviewers if he leave a comment and not in a list yet.
    """
    if not created:
        return
    Applicant = apps.get_model('admission', 'Applicant')
    Interview = apps.get_model('admission', 'Interview')
    Comment = apps.get_model('admission', 'Comment')
    interviewers = instance.interview.interviewers.all()
    comments_cnt = Comment.objects.filter(interview=instance.interview).count()
    if len(interviewers) == comments_cnt:
        instance.interview.status = Interview.COMPLETED
        instance.interview.save()
        instance.interview.applicant.status = Applicant.INTERVIEW_COMPLETED
        instance.interview.applicant.save()
    if instance.interviewer not in interviewers and instance.interviewer.is_curator:
        instance.interview.interviewers.add(instance.interviewer)
