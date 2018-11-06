# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand, CommandError
from post_office import mail
from post_office.models import EmailTemplate
from post_office.utils import get_email_template

from admission_test.models import AdmissionTestApplicant
from admission.management.commands._utils import CurrentCampaignsMixin
from admission.models import Applicant


# TODO: remove duplicates

class Command(CurrentCampaignsMixin, BaseCommand):
    help = """Admission campaign start notification"""

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns()
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        # Check template exists
        template_name = "admission-2018-subscribers-notification"
        try:
            # Use post office method for caching purpose
            template = get_email_template(template_name)
        except EmailTemplate.DoesNotExist:
            raise CommandError(f"Email template {template_name} not found")

        subscribers = AdmissionTestApplicant.objects.only("yandex_id", "email")
        filters = {
            "campaign_id__in": [c.pk for c in campaigns]
        }
        total = 0
        generated = 0
        for subscriber in subscribers.iterator():
            total += 1
            if not Applicant.objects.filter(yandex_id=subscriber.yandex_id,
                                            **filters).exists():
                recipients = [subscriber.email]
                mail.send(
                    recipients,
                    sender='CS центр <info@compscicenter.ru>',
                    template=template,
                    # Render on delivery, we have no really big amount of
                    # emails to think about saving CPU time
                    render_on_delivery=True,
                    backend='ses',
                )
                generated += 1
        self.stdout.write(f"Total: {total}")
        self.stdout.write(f"Generated: {generated}")
