# -*- coding: utf-8 -*-
import csv
from datetime import datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import formats
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
        parser.add_argument(
            '--scheduled_time', type=str,
            help='Scheduled time in UTC [YYYY-MM-DD HH:MM]')

    def handle(self, *args, **options):
        file_path = options["src"]
        header_from = options["from"]
        template_name = options['template']
        if template_name:
            try:
                template = get_email_template(template_name)
            except EmailTemplate.DoesNotExist:
                raise CommandError(f"Email template {template_name} not found")
        scheduled_time = options['scheduled_time']
        if scheduled_time is not None:
            try:
                scheduled_time = datetime.fromisoformat(scheduled_time)
            except ValueError:
                raise CommandError(f"Wrong scheduled time format")

        self.stdout.write(f"Subject: {template.subject}")
        self.stdout.write(f"From: {header_from}")
        if scheduled_time:
            time_display = formats.date_format(scheduled_time, 'DATETIME_FORMAT')
        else:
            time_display = 'now'
        self.stdout.write(f"Scheduled Time: {time_display}")
        if input("Continue? [y/n]") != "y":
            self.stdout.write("Canceled")
            return

        with open(file_path, "r") as f:
            reader = csv.DictReader(f)
            if "email" not in reader.fieldnames:
                raise CommandError("Add `email` header")
            if not template_name and "template_name" not in reader.fieldnames:
                raise CommandError("Provide template name in csv headers or "
                                   "with command argument")

            generated = 0
            for row in reader:
                row = {k: (v.strip() if v is not None else "")
                       for k, v in row.items()}
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
                        scheduled_time=scheduled_time,
                        template=template,
                        context=context,
                        # This option allows filtering emails and
                        # avoid duplicates
                        render_on_delivery=True,
                        backend='ses',
                    )
                    generated += 1
            self.stdout.write("Generated emails: {}".format(generated))
            self.stdout.write("Done")
