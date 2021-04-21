from django.core.exceptions import ValidationError
from django.core.management import BaseCommand, CommandError

from admission.constants import ChallengeStatuses
from admission.models import Applicant, Exam, Contest
from grading.api.yandex_contest import YandexContestAPI, \
    RegisterStatus, ContestAPIError
from ._utils import CurrentCampaignMixin, CustomizeQueryMixin, \
    EmailTemplateMixin, APPROVAL_DIALOG, validate_campaign_passing_score, validate_campaign_contests
from ...services import EmailQueueService


# TODO: filter by status instead of online test exam results?
class Command(CurrentCampaignMixin, CustomizeQueryMixin, EmailTemplateMixin,
              BaseCommand):
    help = """
    For those who passed testing (score >= passing_score) create 
    exam record and register in yandex contest.
    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--send-email', action='store_true',
            dest='send_email',
            help='Send notification with details')

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options, confirm=False)

        send_email = options['send_email']
        send_email_display = "enabled" if send_email else "disabled"
        self.stdout.write(f"Email notifications are {send_email_display}")

        errors = []
        for campaign in campaigns:
            try:
                validate_campaign_passing_score(campaign)
            except ValidationError as e:
                errors.append(e.message)
            try:
                validate_campaign_contests(campaign, contest_type=Contest.TYPE_EXAM)
            except ValidationError as e:
                errors.append(e.message)
            if send_email and not campaign.template_exam_invitation:
                errors.append(f"Exam invitation email template for campaign '{campaign}' not found")
        if errors:
            raise CommandError("\n".join(errors))

        if input(APPROVAL_DIALOG) != "y":
            raise CommandError("Error asking for approval. Canceled")

        manager = self.get_manager(Applicant, options)

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
                    if send_email and exam.status != ChallengeStatuses.NEW:
                        e, created = EmailQueueService.new_exam_invitation(a)
                        emails_generated += created
            self.stdout.write(f"\tNew exam records: {new_records}")
            self.stdout.write(f"\tTotal: {total}")
            if send_email:
                self.stdout.write(f"\tNew emails: {emails_generated}")
        self.stdout.write("Done")
