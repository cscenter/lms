# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.apps import apps


def post_save_interview_update_applicant_status(sender, instance, created,
                                                  *args, **kwargs):
    if not created:
        return
    Applicant = apps.get_model('admission', 'Applicant')
    instance.applicant.status = Applicant.INTERVIEW_ASSIGNED
    instance.applicant.save()


def post_save_interview_comment(sender, instance, created,
                                *args, **kwargs):
    """Set interview status to `completed` if all interviewers leave a comment
    """
    if not created:
        return
    Interview = apps.get_model('admission', 'Interview')
    Comment = apps.get_model('admission', 'Comment')
    interviewers_cnt = len(instance.interview.interviewers.all())
    comments_cnt = Comment.objects.filter(interview=instance.interview).count()
    if interviewers_cnt == comments_cnt:
        instance.interview.status = Interview.COMPLETED
        instance.interview.save()
