# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import tablib
from django.core.management.base import BaseCommand, CommandError
from post_office import mail
from post_office.models import EmailTemplate, Email
from post_office.utils import get_email_template


class Command(BaseCommand):
    help = """
    Generate emails from csv and add them to django post_office mailing queue.
    Sender is info@compscicenter.ru

    Provide `email` column header in csv. 
    Other columns will be added to email context.
    """

    def add_arguments(self, parser):
        parser.add_argument('src', metavar='SRC',
                            help='path to file with emails')
        parser.add_argument(
            '--template', type=str,
            help='Post office email template name')

    def handle(self, *args, **options):
        file_path = options["src"]
        if not options['template']:
            raise CommandError("Provide template name")
        template_name = options['template']
        try:
            # Use post office method for caching purpose
            template = get_email_template(template_name)
        except EmailTemplate.DoesNotExist:
            raise CommandError("Email template {} "
                               "not found".format(template_name))

        with open(file_path, "r") as f:
            data = tablib.Dataset().load(f.read(), format='csv')
            if "email" not in data.headers:
                raise CommandError("Add `email` header")
            generated = 0
            for row in data.dict:
                recipients = row["email"]  # Or provide list
                if not Email.objects.filter(to=recipients,
                                            template=template).exists():
                    context = row.copy()
                    del context['email']
                    mail.send(
                        recipients,
                        sender='info@compscicenter.ru',
                        template=template,
                        context=context,
                        # Render on delivery, we have no really big amount of
                        # emails to think about saving CPU time
                        render_on_delivery=True,
                        backend='ses',
                    )
                    generated += 1
            self.stdout.write("Generated emails: {}".format(generated))
            self.stdout.write("Done")
