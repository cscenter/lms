from typing import Optional

from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import ImageField, Max, Prefetch, Q
from django.urls import reverse
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, ChoiceItem, C
from model_utils.fields import AutoCreatedField, AutoLastModifiedField

from contests.api.yandex_contest import SubmissionVerdict
from contests.constants import YANDEX_SUBMISSION_REPORT_URL
from learning.models import AssignmentComment


class YandexCompilers(DjangoChoices):
    fbc = C("fbc", "Free Basic 1.04")
    c11_x86 = C("c11_x86", "c 11 x32 4.9")
    clang_c11 = C("clang_c11", "Сlang c11 3.8")
    plain_c = C("plain_c", "GNU c 4.9")
    plain_c_x32 = C("plain_c_x32", "GNU c x32 4.9")
    mono_csharp = C("mono_csharp", "Mono C# 5.2.0")
    c11 = C("c11", "GNU c11 4.9")
    clang_cxx11 = C("clang_cxx11", "Clang cxx11 3.8")
    gcc = C("gcc", "GNU c++ 4.9")
    gcc0x = C("gcc0x", "GNU c++ 11 4.9")
    gcc0x_x32 = C("gcc0x_x32", "GNU c++ 11 x32 4.9")
    gcc7_3 = C("gcc7_3", "GNU c++17 7.3")
    dmd = C("dmd", "dmd")
    gdc = C("gdc", "GDC 4.9")
    dcc = C("dcc", "Delphi 2.4.4")
    gc = C("gc", "gc go")
    gccgo = C("gccgo", "gcc go")
    haskell = C("haskell", "Haskell 4.7.1")
    java7 = C("java7", "Oracle Java 7")
    java7_x32 = C("java7_x32", "Oracle Java 7 x32")
    java8 = C("java8", "Oracle Java 8")
    kotlin = C("kotlin", "Kotlin 1.1.50 (JRE 1.8.0)")
    nodejs = C("nodejs", "Node JS 0.10.28")
    ocaml4 = C("ocaml4", "ocaml 4.02.3")
    fpc = C("fpc", "Free pascal 2.4.4")
    perl = C("perl", "Perl 5.14")
    php = C("php", "PHP 5.3.10")
    pypy4 = C("pypy4", "pypy4 ")
    python2_6 = C("python2_6", "Python 2.7")
    python3_4 = C("python3_4", "Python 3.4.3")
    r_core = C("r_core", "R")
    ruby = C("ruby", "Ruby 1.9.3")
    ruby2 = C("ruby2", "ruby 2.2.3")
    rust = C("rust", "rust 1.2")
    scala = C("scala", "Scala 2.9.1")
    bash = C("bash", "GNU bash 4.2.24")
    Others = C("Others", "None")


class CheckingSystemTypes(DjangoChoices):
    yandex = ChoiceItem('ya', _("Yandex.Contest"))


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
        if self.type == CheckingSystemTypes.yandex:
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
        if self.checking_system.type == CheckingSystemTypes.yandex:
            required_settings = ['contest_id', 'problem_id']
            for key in required_settings:
                if key not in self.settings:
                    # FIXME: add translation _("Убедитесь, что указаны настройки: {}")
                    msg = _("Please check that the following settings "
                            "are provided: {}")
                    settings_needed = ', '.join(required_settings)
                    raise ValidationError(msg.format(settings_needed))


class SubmissionStatus(DjangoChoices):
    NEW = ChoiceItem(1, _("New"), icon='time')
    SUBMIT_FAIL = ChoiceItem(20, _("Not Submitted"), icon='cross')
    CHECKING = ChoiceItem(30, _("Checking"), icon='time')
    FAILED = ChoiceItem(40, _("Wrong Answer"), icon='cross')
    PASSED = ChoiceItem(50, _("Correct Answer"), icon='checkmark')

    checked_statuses = [FAILED, PASSED]

    @classmethod
    def was_checked(cls, status):
        return status in cls.checked_statuses


class Submission(models.Model):
    STATUSES = SubmissionStatus

    created_at = AutoCreatedField(_('created'))
    modified_at = AutoLastModifiedField(_('modified'))
    assignment_comment = models.OneToOneField(
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
        assignment = self.assignment_comment.student_assignment.assignment
        checking_system_type = assignment.checker.checking_system.type
        return CheckingSystemTypes.get_choice(checking_system_type)

    @property
    def status_choice(self):
        return SubmissionStatus.get_choice(self.status)

    @property
    def get_report_url(self):
        if self.checking_system_choice.value == CheckingSystemTypes.yandex:
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
