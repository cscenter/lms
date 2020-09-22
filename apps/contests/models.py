from typing import Optional

from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import ugettext_lazy as _
from model_utils.fields import AutoCreatedField, AutoLastModifiedField

from contests.api.yandex_contest import SubmissionVerdict, \
    YANDEX_SUBMISSION_REPORT_URL
from contests.constants import CheckingSystemTypes, SubmissionStatus
from learning.models import AssignmentComment


class CheckingSystem(models.Model):
    created_at = AutoCreatedField(_('created'))
    name = models.CharField(_("CheckingSystem|Name"),
                            max_length=80)
    type = models.CharField(_("CheckingSystem|Type"), max_length=42,
                            choices=CheckingSystemTypes.choices)
    description = models.TextField(
        verbose_name=_("What can it be used for?"),
        blank=True
    )
    settings = JSONField(
        verbose_name=_("CheckingSystem|Details"),
        blank=True,
        default=dict,
        help_text=_("Access token, etc")
    )

    class Meta:
        verbose_name = _("Checking System")
        verbose_name_plural = _("Checking Systems")

    def __str__(self):
        return self.name

    def clean(self):
        if self.type == CheckingSystemTypes.YANDEX:
            has_access_token = 'access_token' in self.settings
            use_participant_oauth = ('use_participant_oauth' in self.settings
                                     and self.settings['use_participant_oauth'])
            if not (has_access_token or use_participant_oauth):
                raise ValidationError(_("Access token should be specified,"
                                        "or participant's OAuth token should"
                                        "be used for submission."))


class Checker(models.Model):
    checking_system = models.ForeignKey(
        CheckingSystem,
        verbose_name=_("Checking System"),
        on_delete=models.CASCADE
    )
    url = models.URLField(_("Checker|URL"), blank=True)
    settings = JSONField(
        verbose_name=_("Checker|Settings"),
        blank=True,
        default=dict,
        help_text=_("Contest id, problem id, etc")
    )

    class Meta:
        verbose_name = _("Checker")
        verbose_name_plural = _("Checkers")

    def __str__(self):
        return (self.checking_system.name +
                f' [{", ".join(f"{k}: {v}" for k, v in self.settings.items())}]')

    def clean(self):
        if self.checking_system.type == CheckingSystemTypes.YANDEX:
            required_settings = ['contest_id', 'problem_id']
            for key in required_settings:
                if key not in self.settings:
                    # FIXME: add translation _("Убедитесь, что указаны настройки: {}")
                    msg = _("Please check that the following settings "
                            "are provided: {}")
                    settings_needed = ', '.join(required_settings)
                    raise ValidationError(msg.format(settings_needed))


class Submission(models.Model):
    STATUSES = SubmissionStatus

    created_at = AutoCreatedField(_('created'))
    modified_at = AutoLastModifiedField(_('modified'))
    assignment_submission = models.OneToOneField(
        AssignmentComment,
        verbose_name=_("Assignment Submission"),
        on_delete=models.CASCADE
    )
    status = models.IntegerField(
        _("Status"),
        default=SubmissionStatus.NEW,
        choices=SubmissionStatus.choices)
    settings = JSONField(
        verbose_name=_("Settings"),
        blank=True,
        default=dict,
        help_text=_("Selected compiler, etc")
    )
    meta = JSONField(
        verbose_name=_("Meta"),
        blank=True,
        default=dict,
        help_text=_("Returned submission id or error details")
    )

    class Meta:
        verbose_name = _("Submission")
        verbose_name_plural = _("Submissions")

    @property
    def checking_system_choice(self):
        assignment = self.assignment_submission.student_assignment.assignment
        checking_system_type = assignment.checker.checking_system.type
        return CheckingSystemTypes.get_choice(checking_system_type)

    @property
    def status_choice(self):
        return SubmissionStatus.get_choice(self.status)

    @property
    def get_report_url(self):
        if self.checking_system_choice.value == CheckingSystemTypes.YANDEX:
            required_attributes = ['contestId', 'runId']
            for attr in required_attributes:
                if attr not in self.meta:
                    return None
            contest_id = self.meta['contestId']
            run_id = self.meta['runId']
            return YANDEX_SUBMISSION_REPORT_URL.format(contest_id=contest_id,
                                                       run_id=run_id)
        return None

    def get_verdict(self) -> Optional[str]:
        if not SubmissionStatus.was_checked(self.status):
            return self.status_choice.label
        if "verdict" in self.meta:
            verdict = self.meta["verdict"]
            try:
                output = SubmissionVerdict(verdict).name
                if verdict == SubmissionVerdict.WA.value:
                    for t in self.meta.get('checkerLog', []):
                        if t["verdict"] == SubmissionVerdict.WA.value:
                            output += f" [тест {t['sequenceNumber']}]"
                            break
                return output
            except ValueError:
                return verdict
        return self.status_choice.label
