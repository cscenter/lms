from django.core.management.base import BaseCommand, CommandError
from post_office import mail
from post_office.models import Email
from post_office.utils import get_email_template

from admission.models import Applicant
from admission.services import get_email_from
from ._utils import EmailTemplateMixin, CurrentCampaignMixin, APPROVAL_DIALOG


class ExamResultStatus:
    FAIL = "fail"
    SUCCESS = "success"


def get_exam_results_template_pattern(applicant, patterns):
    if applicant.status == Applicant.INTERVIEW_TOBE_SCHEDULED:
        return patterns[ExamResultStatus.SUCCESS]
    else:
        return patterns[ExamResultStatus.FAIL]


class Command(EmailTemplateMixin, CurrentCampaignMixin, BaseCommand):
    help = """Generate emails about exam results."""

    TEMPLATE_PATTERN = "admission-{year}-{branch_code}-exam-{status}"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--fail-only', action='store_true',
            dest="fail_only",
            help="Send emails only to those who didn't pass to the next stage")

    def handle(self, *args, **options):
        campaigns = self.get_current_campaigns(options, confirm=False)
        # Collect all template patterns, then validate them
        template_name_patterns = {}
        result_statuses = [ExamResultStatus.FAIL]
        if not options["fail_only"]:
            result_statuses.append(ExamResultStatus.SUCCESS)
        for status in result_statuses:
            pattern = options['template_pattern'] or self.TEMPLATE_PATTERN
            pattern = pattern.replace("{status}", status)
            template_name_patterns[status] = pattern
        self.validate_templates(campaigns, template_name_patterns.values())

        for campaign in campaigns:
            self.stdout.write("{}:".format(campaign))
            email_from = get_email_from(campaign)

            statuses = [Applicant.REJECTED_BY_EXAM]
            if not options["fail_only"]:
                statuses.append(Applicant.INTERVIEW_TOBE_SCHEDULED)
            applicants = (Applicant.objects
                          .filter(campaign=campaign.pk,
                                  status__in=statuses)
                          .only("email", "status"))
            succeed = 0
            total = 0
            generated = 0
            for a in applicants.iterator():
                total += 1
                succeed += int(a.status == Applicant.INTERVIEW_TOBE_SCHEDULED)
                pattern = get_exam_results_template_pattern(a, template_name_patterns)
                template_name = self.get_template_name(campaign, pattern)
                template = get_email_template(template_name)
                recipients = [a.email]
                if not Email.objects.filter(to=recipients,
                                            template=template).exists():
                    context = {
                        'BRANCH': campaign.branch.name
                    }
                    mail.send(
                        recipients,
                        sender=email_from,
                        template=template,
                        # If emails rendered on delivery, they will store
                        # value of the template id. It makes
                        # `Email.objects.exists()` work correctly.
                        render_on_delivery=True,
                        context=context,
                        backend='ses',
                    )
                    generated += 1
            self.stdout.write("Total: {}".format(total))
            self.stdout.write("Succeed: {}".format(succeed))
            self.stdout.write("Fail: {}".format(total - succeed))
            self.stdout.write("Emails generated: {}".format(generated))
        self.stdout.write("Done")
