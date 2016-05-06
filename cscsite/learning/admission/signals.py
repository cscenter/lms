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
