# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.core.management.base import BaseCommand, CommandError
from post_office import mail

from learning.admission.models import Applicant, Exam


# ./manage.py email_online_exam_contest_checked  --template=admission-2016-online-exam-checked --campaign_id=2
class Command(BaseCommand):
    help = 'Generate mails about contest check completeness'

    def add_arguments(self, parser):
        parser.add_argument('--template', type=str,
                        dest='template_name',
                        help='Email template')
        parser.add_argument('--campaign_id', type=int,
                            dest='campaign_id',
                            help='Campaign #ID#')

    def handle(self, *args, **options):
        template_name = options["template_name"]
        campaign_id = options["campaign_id"]
        if not template_name:
            raise CommandError("You must choose template name")
        if not campaign_id:
            raise CommandError("Specify admissions campaign ID")


        exam_results = (
            Exam.objects
                # Note: Django generates query like
                #  filter rows with status != 'reject_cheating' or with NULL status
                .filter(applicant__campaign=campaign_id)
                .exclude(applicant__status=Applicant.REJECTED_BY_CHEATING)
                .select_related("applicant")
        )
        print(exam_results.query)

        for e in exam_results:
            applicant = e.applicant
            mail.send(
                [applicant.email],
                sender='info@compscicenter.ru',
                template=template_name,
                backend='ses',
            )


