# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.apps import apps


def post_save_interview_update_applicant_status(sender, instance, created,
                                                  *args, **kwargs):
    if not created:
        return
    Applicant = apps.get_model('admission', 'Applicant')
    instance.applicant.status = Applicant.INTERVIEW_SCHEDULED
    instance.applicant.save()


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
