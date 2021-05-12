from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.utils.encoding import force_str
from django.utils.html import strip_tags


class Command(BaseCommand):
    help = 'Send real email for test purpose'

    def add_arguments(self, parser):
        parser.add_argument('email_to')
        parser.add_argument('subject')
        parser.add_argument('html_body', type=lambda s: force_str(s, 'utf8'))

    def handle(self, *args, **options):
        html_content = options['html_body']
        text_content = strip_tags(html_content)

        msg = EmailMultiAlternatives(options['subject'],
                                     text_content,
                                     settings.DEFAULT_FROM_EMAIL,
                                     [options['email_to']])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
