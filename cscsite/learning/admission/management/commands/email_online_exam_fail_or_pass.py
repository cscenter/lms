# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.core.management.base import BaseCommand, CommandError
from post_office import mail

from learning.admission.models import Applicant, Exam


# ./manage.py email_online_exam_fail_or_pass  --template_fail=admission-2016-online-exam-fail --campaign_id=2
class Command(BaseCommand):
    help = 'Generate emails about online exam results'

    def add_arguments(self, parser):
        parser.add_argument('--campaign_id', type=int,
                            dest='campaign_id',
                            help='Campaign #ID#')
        parser.add_argument('--template_fail', type=str,
                            dest='email_template_fail',
                            help='Email template name from django-post for '
                                 'those who fail exam')
        parser.add_argument('--template_success', type=str,
                            dest='email_template_success',
                            help='Email template name from django-post '
                                 'for those who pass to next (interview) stage')

    def handle(self, *args, **options):
        email_template_fail = options["email_template_fail"]
        email_template_success = options["email_template_success"]
        campaign_id = options["campaign_id"]
        if not email_template_fail or not email_template_success:
            raise CommandError("Provide both email templates names for "
                               "django-post")
        if not campaign_id:
            raise CommandError("Specify admissions campaign ID")

        success_applicants = (Applicant.objects
                              .filter(campaign=campaign_id,
                                      status=Applicant.INTERVIEW_TOBE_SCHEDULED))
        print("Emails with success: {}".format(len(success_applicants)))
        for applicant in success_applicants:
            mail.send(
                [applicant.email],
                sender='info@compscicenter.ru',
                template=email_template_success,
                backend='ses',
            )
        fail_applicants = (Applicant.objects
                           .filter(campaign=campaign_id,
                                   status=Applicant.REJECTED_BY_EXAM))
        print("Emails with fail: {}".format(len(fail_applicants)))
        for applicant in fail_applicants:
            mail.send(
                [applicant.email],
                sender='info@compscicenter.ru',
                template=email_template_fail,
                backend='ses',
            )

