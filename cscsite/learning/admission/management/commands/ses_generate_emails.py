# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError
from django.utils.html import strip_tags, linebreaks
from post_office import mail

from learning.admission.models import Test, Applicant

# ./manage.py ses_generate_emails --passing_score=7 --template=admission-2016-online-test-success --campaign_id=2
class Command(BaseCommand):
    help = 'Generate mailing list for choosing template and action'

    def add_arguments(self, parser):
        parser.add_argument('--template', type=str,
                        dest='template_name',
                        help='Email template')
        parser.add_argument('--passing_score', type=int,
                            help='Create records for applicants with online_test results above this value')
        parser.add_argument('--campaign_id', type=int,
                            dest='campaign_id',
                            help='ID of imported campaign')

    def handle(self, *args, **options):
        template_name = options["template_name"]
        campaign_id = options["campaign_id"]
        passing_score = options["passing_score"]
        if not passing_score:
            raise CommandError("Empty passing score")
        if not template_name:
            raise CommandError("You must choose template name")
        if not campaign_id:
            raise CommandError("Specify admissions campaign ID")

        success_applicants = (Applicant.objects.filter(campaign_id=campaign_id,
                                                       online_test__score__gte=passing_score)
                              .select_related("online_test", "exam"))

        for a in success_applicants[:3]:
            if not a.exam:
                print("what are you doing here, man?")
            score = int(a.online_test.score)
            score_str = str(score) + " балл" + self.pluralize(score)
            mail.send(
                [a.email],
                sender='info@compscicenter.ru',
                template=template_name,
                context={
                    'SCORE': score_str,
                    'LOGIN': a.yandex_id,
                    'LINK': "https://contest.yandex.ru/contest/{}/".format(a.exam.yandex_contest_id)
                },
                backend='ses',
            )

    # shitty code
    def pluralize(self, value):
        endings = ["a", "", "ов"]
        if value % 100 in (11, 12, 13, 14):
            return endings[2]
        if value % 10 == 1:
            return endings[0]
        if value % 10 in (2, 3, 4):
            return endings[1]
        else:
            return endings[2]


