# -*- coding: utf-8 -*-

from django.core.management import BaseCommand, CommandError

from admission.constants import ChallengeStatuses
from admission.models import Applicant, Exam, Contest
from api.providers.yandex_contest import YandexContestAPI, \
    RegisterStatus, ContestAPIError
from ._utils import CurrentCampaignMixin, CustomizeQueryMixin, \
    EmailTemplateMixin
from ...services import EmailQueueService


class Command(CurrentCampaignMixin, CustomizeQueryMixin, EmailTemplateMixin,
              BaseCommand):
    help = """
    For those who passed testing (score >= passing_score) create 
    exam record and register in yandex contest.
 
    Note: 
        This command does not update applicant status
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--send-email', action='store_true',
            dest='send_notification',
            help='Send notification with details')

    def handle(self, *args, **options):
        send_notification = options['send_notification']
        if send_notification:
            self.stdout.write("Email notifications are enabled")
        else:
            self.stdout.write("Email notifications are disabled")
        campaigns = self.get_current_campaigns(options)
        if input(self.CURRENT_CAMPAIGNS_AGREE) != "y":
            self.stdout.write("Canceled")
            return

        manager = self.get_manager(Applicant, options)
        # Validation
        has_errors = False
        for campaign in campaigns:
            self.stdout.write(f"Validating {campaign}:")
            errors = []
            if not campaign.online_test_passing_score:
                msg = f"\tZero passing score settings"
                errors.append(msg)
            # Make sure we have exam contests associated with campaign
            # Otherwise we can't assign random contest number
            if not Contest.objects.filter(type=Contest.TYPE_EXAM,
                                          campaign=campaign).exists():
                msg = f"\tExam contests not found"
                errors.append(msg)
            if send_notification and not campaign.template_exam_invitation:
                msg = f"\tExam invitation email template not found"
                errors.append(msg)
            if errors:
                has_errors = True
                self.stdout.write("\n".join(errors))
        if has_errors:
            raise CommandError("Campaign validation errors")

        for campaign in campaigns:
            self.stdout.write(f"Processing {campaign}:")
            api = YandexContestAPI(access_token=campaign.access_token,
                                   refresh_token=campaign.refresh_token)
            total = 0
            new_records = 0
            emails_generated = 0
            applicants = (manager.filter(campaign_id=campaign.pk,
                                         online_test__score__gte=campaign.online_test_passing_score))
            for a in applicants:
                exam, created = Exam.objects.get_or_create(
                    applicant=a,
                    defaults={"status": ChallengeStatuses.NEW})
                if created:
                    new_records += 1
                total += 1
                if created or exam.status == ChallengeStatuses.NEW:
                    try:
                        exam.register_in_contest(api)
                    except ContestAPIError as e:
                        if e.code == RegisterStatus.BAD_TOKEN:
                            self.stdout.write(f"Bad campaign token {campaign}")
                            break
                        self.stdout.write(
                            f"API request error for applicant {a}. "
                            f"Code: {e.code}. Message: {e.message}"
                        )
                        continue
                    if send_notification and exam.status != ChallengeStatuses.NEW:
                        e, created = EmailQueueService.new_exam_invitation(a)
                        emails_generated += created
            self.stdout.write(f"\tNew exam records: {new_records}")
            self.stdout.write(f"\tTotal: {total}")
            if send_notification:
                self.stdout.write(f"\tNew emails: {emails_generated}")
        self.stdout.write("Done")
