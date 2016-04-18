# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError
from django.utils.html import strip_tags, linebreaks
from post_office import mail

from learning.admission.models import Test


class Command(BaseCommand):
    help = 'Generate mailing list for choosing template and action'

    def add_arguments(self, parser):
        parser.add_argument('--template', type=str,
                        dest='template_name',
                        help='Email template')
        parser.add_argument('--campaign_id', type=int,
                            dest='campaign_id',
                            help='ID of imported campaign')

    def handle(self, *args, **options):
        template_name = options["template_name"]
        campaign_id = options["campaign_id"]
        if not template_name:
            raise CommandError("You must choose template name")
        if not campaign_id:
            raise CommandError("Specify admissions campaign ID")


        tests = (Test.objects
                     .filter(applicant__campaign=campaign_id)
                     .select_related("applicant")
                     .only("applicant__yandex_id",
                           "score"))
        for test in tests:
            mail.send(
                [test.applicant.yandex_id],
                sender='info@compscicenter.ru',
                template=template_name,
                context={
                    'score': test.score,
                    'yandex_login': test.applicant.yandex_id
                },
                backend='ses',
            )


