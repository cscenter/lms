# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.apps import apps


def post_save_interview(sender, instance, created,
                        *args, **kwargs):
    """
    Set appropriate applicant status based on interview status.
    Revert applicant status to `INTERVIEW_TOBE_SCHEDULED` when interview
    status was changed to `CANCELED` or `DEFERRED`. Presume we have no
    concurrent  active interviews for one applicant, it means we first
    canceled old one and only after that create the new one.
    """
    Applicant = apps.get_model('admission', 'Applicant')
    Interview = apps.get_model('admission', 'Interview')
    interview = instance
    if created and interview.status in [Interview.APPROVAL, Interview.WAITING]:
        interview.applicant.status = Applicant.INTERVIEW_SCHEDULED
    elif interview.status in [Interview.CANCELED, Interview.DEFERRED]:
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
