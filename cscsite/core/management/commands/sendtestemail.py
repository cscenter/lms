# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.utils.html import strip_tags, linebreaks


class Command(BaseCommand):
    help = 'Send real email for test purpose'

    def add_arguments(self, parser):
        parser.add_argument('email_to')
        parser.add_argument('subject')
        parser.add_argument('html_body', type=lambda s: unicode(s, 'utf8'))
        parser.add_argument('--email_from',
                            dest='email_from',
                            default='test@compscicenter.ru',
                            help='Provide email from')

    def handle(self, *args, **options):
        html_content = linebreaks(options['html_body'])
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(options['subject'],
                                     text_content,
                                     options['email_from'],
                                     [options['email_to']])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
