from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from django.core.management.base import BaseCommand

from admission.models import Applicant
from admission.services import get_email_from

from ._utils import CurrentCampaignMixin, EmailTemplateMixin


class ExamResultStatus:
    FAIL = "fail"
    CHEATER = "cheater"
    SUCCESS = "success"


def get_exam_results_template_pattern(status: str, initial_pattern: str, **kwargs):
    status_mapping = {
        Applicant.INTERVIEW_TOBE_SCHEDULED: ExamResultStatus.SUCCESS,
        Applicant.REJECTED_BY_EXAM_CHEATING: ExamResultStatus.CHEATER,
        Applicant.REJECTED_BY_EXAM: ExamResultStatus.FAIL,
    }
    status = status_mapping.get(status)
    if status is None:
        raise NotImplementedError(f"Mapping from {status} to pattern status is not implemented.")
    return initial_pattern.format(status=status, **kwargs)


class Command(EmailTemplateMixin, CurrentCampaignMixin, BaseCommand):
    help = """Generate emails about exam results."""

    TEMPLATE_PATTERN = "shad-admission-{year}-exam-{status}-{branch_code}"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--commit",
            action="store_true",
            default=False,
            dest="commit",
            help="Actually send emails."
        )
        parser.add_argument(
            "--applicant_id",
            dest="applicant_id",
            help="Send email only for applicant.id == applicant_id"
        )

    def handle(self, *args, **options):
        commit = options['commit']
        applicant_id = options.get('applicant_id')
        campaigns = self.get_current_campaigns(
            options, branch_is_required=True, confirm=False
        )
        assert len(campaigns) == 1
        campaign = campaigns[0]

        pattern = options["template_pattern"] or self.TEMPLATE_PATTERN
        statuses = [
            Applicant.REJECTED_BY_EXAM,
            Applicant.INTERVIEW_TOBE_SCHEDULED,
            Applicant.REJECTED_BY_EXAM_CHEATING,
        ]

        self.stdout.write(f"Templates for campaign: {campaign}")
        status_to_pattern = {}
        for status in statuses:
            status_pattern = get_exam_results_template_pattern(
                status,
                pattern,
                year=campaign.year,
                branch_code=campaign.branch.code,
            )
            self.stdout.write(f"\t {status_pattern}")
            status_to_pattern[status] = get_email_template(status_pattern)
        email_from = get_email_from(campaign)

        if applicant_id:
            applicants = Applicant.objects.filter(id=applicant_id)
        else:
            applicants = (
                Applicant.objects.filter(campaign=campaign.pk, status__in=statuses)
                .select_related("exam")
                .only("email", "status")
            )

        succeed = 0
        cheater = 0
        failed = 0
        total = 0
        generated = 0
        for a in applicants.iterator():
            total += 1
            succeed += int(a.status == Applicant.INTERVIEW_TOBE_SCHEDULED)
            cheater += int(a.status == Applicant.REJECTED_BY_EXAM_CHEATING)
            failed += int(a.status == Applicant.REJECTED_BY_EXAM)
            template = status_to_pattern[a.status]
            recipients = [a.email]
            if not Email.objects.filter(to=recipients, template=template).exists():
                context = {
                    "BRANCH": campaign.branch.name,
                    "name": a.first_name,
                }
                if commit:
                    mail.send(
                        recipients,
                        sender=email_from,
                        template=template,
                        # If emails rendered on delivery, they will store
                        # value of the template id. It makes
                        # `Email.objects.exists()` work correctly.
                        render_on_delivery=True,
                        context=context,
                        backend="ses",
                    )
                    generated += 1
        self.stdout.write("Total: {}".format(total))
        self.stdout.write("Succeed: {}".format(succeed))
        self.stdout.write("Cheater: {}".format(cheater))
        self.stdout.write("Fail: {}".format(failed))
        self.stdout.write("Emails generated: {}".format(generated))
        if commit:
            self.stdout.write("Done")
        else:
            self.stdout.write("Emails is not sent. Use --commit to send them.")
