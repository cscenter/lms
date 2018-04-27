# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import csv

import tablib
from django.core.management.base import BaseCommand, CommandError
from post_office import mail
from post_office.models import EmailTemplate, Email
from post_office.utils import get_email_template


class Command(BaseCommand):
    help = """
    Generates emails from csv and add them to `post_office` mailing queue.

    Provide `email` column header in csv. 
    Other columns will be added to email context.
    """

    def add_arguments(self, parser):
        parser.add_argument('src', metavar='PATH_TO_CSV',
                            help='path to file with emails')
        parser.add_argument(
            '--template', type=str, metavar='NAME',
            help='Post office email template name')
        parser.add_argument(
            '--from', type=str,
            default='noreply@compscicenter.ru',
            help='`From` header, e.g. `CS центр <info@compscicenter.ru>`')

    def handle(self, *args, **options):
        file_path = options["src"]
        header_from = options["from"]
        template_name = options['template']
        if template_name:
            try:
                template = get_email_template(template_name)
            except EmailTemplate.DoesNotExist:
                raise CommandError(f"Email template {template_name} not found")

        with open(file_path, "r") as f:
            reader = csv.DictReader(f)
            if "email" not in reader.fieldnames:
                raise CommandError("Add `email` header")
            if not template_name and "template_name" not in reader.fieldnames:
                raise CommandError("Provide template name in csv headers or "
                                   "with command argument")

            generated = 0
            for row in reader:
                row = {k: row[k].strip() for k in row}
                if "template_name" in row:
                    template_name = row["template_name"]
                    try:
                        template = get_email_template(template_name)
                    except EmailTemplate.DoesNotExist:
                        msg = f"Template {template_name} not found. Skip row."
                        self.stdout.write(msg)

                recipient = row["email"]
                if not Email.objects.filter(to=recipient,
                                            template=template).exists():
                    context = {k: row[k] for k in row
                               if k != "email" and k != "template_name"}
                    mail.send(
                        recipient,
                        sender=header_from,
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
