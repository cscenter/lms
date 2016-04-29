# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from collections import OrderedDict

from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.validators import RegexValidator, MinValueValidator, \
    MaxValueValidator
from django.db import models
from django.utils.encoding import python_2_unicode_compatible, smart_text
from jsonfield import JSONField
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel

from learning.settings import PARTICIPANT_GROUPS


@python_2_unicode_compatible
class Campaign(models.Model):
    name = models.CharField(_("Campaign|Campaign_name"), max_length=140)
    code = models.CharField(_("Campaign|Code"), max_length=140,
                            help_text=_("Will be displayed in admin select"))
    online_test_max_score = models.SmallIntegerField(
        _("Campaign|Test_max_score"))
    online_test_passing_score = models.SmallIntegerField(
        _("Campaign|Test_passing_score"))
    exam_max_score = models.SmallIntegerField(
        _("Campaign|Exam_max_score"))
    exam_passing_score = models.SmallIntegerField(
        _("Campaign|Exam_passing_score"))

    class Meta:
        verbose_name = _("Campaign")
        verbose_name_plural = _("Campaigns")

    def __str__(self):
        return smart_text(self.name)


@python_2_unicode_compatible
class Applicant(TimeStampedModel):
    REJECTED_BY_TEST = 'rejected_test'
    REJECTED_BY_CHEATING = 'rejected_cheating'
    REJECTED_BY_EXAM = 'rejected_exam'
    REJECTED_BY_INTERVIEW = 'rejected_interview'
    ACCEPT = 'accept'
    VOLUNTEER = 'volunteer'
    STATUS = (
        (REJECTED_BY_CHEATING, _('Cheating')),
        (REJECTED_BY_TEST, _('Rejected by test')),
        (REJECTED_BY_EXAM, _('Rejected by exam')),
        (REJECTED_BY_INTERVIEW, _('Rejected by interview')),
        (ACCEPT, _('Accept')),
        (VOLUNTEER, _("Applicant|Volunteer")),
    )
    campaign = models.ForeignKey(
        Campaign,
        verbose_name=_("Applicant|Campaign"),
        on_delete=models.PROTECT,
        related_name="applicants")
    first_name = models.CharField(_("First name"), max_length=255)
    second_name = models.CharField(_("Second name"), max_length=255)
    last_name = models.CharField(_("Last name"), max_length=255)
    email = models.EmailField(
        _("Email"),
        help_text=_("Applicant|email"))
    phone = models.CharField(
        _("Contact phone"),
        max_length=42,
        help_text=_("Applicant|phone"))
    stepic_id = models.PositiveIntegerField(
        _("Stepic ID"),
        help_text=_("Applicant|stepic_id"),
        blank=True,
        null=True)
    yandex_id = models.CharField(
        _("Yandex ID"),
        max_length=80,
        validators=[RegexValidator(regex="^[^@]*$",
                                   message=_("Only the part before "
                                             "\"@yandex.ru\" is expected"))],
        help_text=_("Applicant|yandex_id"))
    yandex_id_normalize = models.CharField(
        _("Yandex ID normalisation"),
        max_length=80,
        help_text=_("Applicant|yandex_id_normalization"))
    github_id = models.CharField(
        _("Github ID"),
        max_length=255,
        help_text=_("Applicant|github_id"),
        null=True,
        blank=True)

    university = models.CharField(
        _("University"),
        help_text=_("Applicant|university"),
        max_length=255)
    faculty = models.TextField(
        _("Faculty"),
        help_text=_("Applicant|faculty"))
    course = models.CharField(
        _("Course"),
        help_text=_("Applicant|course"),
        max_length=355)
    graduate_work = models.TextField(
        _("Graduate work"),
        help_text=_("Applicant|graduate_work_or_dissertation"),
        null=True,
        blank=True)
    experience = models.TextField(
        _("Experience"),
        help_text=_("Applicant|work_or_study_experience"),
        null=True,
        blank=True)
    has_job = models.CharField(
        _("Do you work?"),
        help_text=_("Applicant|has_job"),
        max_length=10,
        null=True,
        blank=True)
    workplace = models.CharField(
        _("Workplace"),
        help_text=_("Applicant|workplace"),
        max_length=255,
        null=True,
        blank=True)
    position = models.CharField(
        _("Position"),
        help_text=_("Applicant|position"),
        max_length=255,
        null=True,
        blank=True)

    motivation = models.TextField(
        _("Your motivation"),
        help_text=_("Applicant|motivation_why"),
        blank=True,
        null=True)
    additional_info = models.TextField(
        _("Additional info from applicant about himself"),
        help_text=_("Applicant|additional_info"),
        blank=True,
        null=True)
    preferred_study_programs = models.CharField(
        _("Study program"),
        help_text=_("Applicant|study_program"),
        max_length=255)
    where_did_you_learn = models.TextField(
        _("Where did you learn?"),
        help_text=_("Applicant|where_did_you_learn_about_cs_center"))
    your_future_plans = models.TextField(
        _("Future plans"),
        help_text=_("Applicant|future_plans"),
        blank=True,
        null=True)
    admin_note = models.TextField(
        _("Admin note"),
        help_text=_("Applicant|admin_note"),
        blank=True,
        null=True)
    status = models.CharField(
        choices=STATUS,
        verbose_name=_("Applicant|Status"),
        blank=True,
        null=True,
        max_length=20)
    uuid = models.UUIDField(editable=False, null=True, blank=True)

    class Meta:
        verbose_name = _("Applicant")
        verbose_name_plural = _("Applicants")

    def get_full_name(self):
        parts = [self.second_name, self.first_name, self.last_name]
        return smart_text(" ".join(part for part in parts if part).strip())

    def clean(self):
        self.yandex_id_normalize = self.yandex_id.lower().replace('-', '.')

    def __str__(self):
        if self.campaign_id:
            return smart_text(
                "{} [{}]".format(self.get_full_name(), self.campaign.code))
        else:
            return smart_text(self.get_full_name())


def contest_assignments_upload_to(instance, filename):
    # TODO: Can be visible for unauthenticated. Is it ok?
    return instance.FILE_PATH_TEMPLATE.format(
        contest_id=instance.contest_id,
        filename=filename)


@python_2_unicode_compatible
class Contest(models.Model):
    FILE_PATH_TEMPLATE = "contest/{contest_id}/assignments/{filename}"

    campaign = models.ForeignKey(
        Campaign,
        verbose_name=_("Contest|Campaign"),
        on_delete=models.PROTECT,
        related_name="contests")
    contest_id = models.CharField(
        _("Contest #ID"),
        help_text=_("Applicant|yandex_contest_id"),
        max_length=42,
        blank=True,
        null=True)

    file = models.FileField(
        _("Assignments in pdf format"),
        blank=True,
        upload_to=contest_assignments_upload_to)

    class Meta:
        verbose_name = _("Contest")
        verbose_name_plural = _("Contests")

    def file_url(self):
        return self.file.url

    def __str__(self):
        return self.contest_id


@python_2_unicode_compatible
class Test(TimeStampedModel):
    applicant = models.OneToOneField(
        Applicant,
        verbose_name=_("Applicant"),
        on_delete=models.PROTECT,
        related_name="online_test")
    details = JSONField(
        load_kwargs={'object_pairs_hook': OrderedDict},
        blank=True,
        null=True,
    )
    # TODO: replace with FK to Contest model?
    yandex_contest_id = models.CharField(
        _("Contest #ID"),
        help_text=_("Applicant|yandex_contest_id"),
        max_length=42,
        blank=True,
        null=True)
    # TODO: replace with integer
    score = models.DecimalField(
        verbose_name=_("Score"),
        max_digits=3,
        decimal_places=1)

    class Meta:
        verbose_name = _("Testing")
        verbose_name_plural = _("Testings")

    def __str__(self):
        """ Import/export get repr before instance created in db."""
        if self.applicant_id:
            return self.applicant.get_full_name()
        else:
            return smart_text(self.score)


@python_2_unicode_compatible
class Exam(TimeStampedModel):
    applicant = models.OneToOneField(
        Applicant,
        verbose_name=_("Applicant"),
        on_delete=models.PROTECT,
        related_name="exam")
    details = JSONField(
        load_kwargs={'object_pairs_hook': OrderedDict},
        blank=True,
        null=True
    )
    # TODO: replace with FK to Contest model! Migrate all data
    yandex_contest_id = models.CharField(
        _("Contest #ID"),
        help_text=_("Applicant|yandex_contest_id"),
        max_length=42,
        blank=True,
        null=True)
    score = models.PositiveSmallIntegerField(
        verbose_name=_("Score"))

    class Meta:
        verbose_name = _("Exam")
        verbose_name_plural = _("Exams")

    def __str__(self):
        """ Import/export get repr before instance created in db."""
        if self.applicant_id:
            return self.applicant.get_full_name()
        else:
            return smart_text(self.score)


@python_2_unicode_compatible
class InterviewAssignment(models.Model):
    campaign = models.ForeignKey(
        Campaign,
        verbose_name=_("InterviewAssignments|Campaign"),
        on_delete=models.PROTECT,
        related_name="interview_assignments")
    name = models.CharField(_("InterviewAssignments|name"), max_length=255)
    description = models.TextField(
        _("Assignment description"),
        help_text=_("TeX support"))

    class Meta:
        verbose_name = _("Interview assignment")
        verbose_name_plural = _("Interview assignments")

    def __str__(self):
        return smart_text(self.name)


@python_2_unicode_compatible
class Interview(TimeStampedModel):
    APPROVAL = 'approval'
    WAITING = 'waiting'
    CANCELED = 'canceled'
    ACCEPT = 'accept'
    DECLINE = 'decline'
    VOLUNTEER = 'volunteer'
    DECISIONS = (
        (APPROVAL, _('Approval')),
        (WAITING, _('Waiting for interview')),
        (CANCELED, _('Canceled')),
        (ACCEPT, _('Accept')),
        (DECLINE, _('Decline')),
        (VOLUNTEER, _("Volunteer")),
    )

    date = models.DateTimeField(_("When"))
    applicant = models.ForeignKey(
        Applicant,
        verbose_name=_("Applicant"),
        on_delete=models.PROTECT,
        related_name="interviews")
    interviewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Interview|Interviewers"),
        limit_choices_to={'groups__pk': PARTICIPANT_GROUPS.INTERVIEWER})

    assignments = models.ManyToManyField(
        'InterviewAssignment',
        verbose_name=_("Interview|Assignments"),
        blank=True)

    # TODO: дублировать в Applicant, если in [accept, decline, volunteer] ?
    decision = models.CharField(
        choices=DECISIONS,
        default=APPROVAL,
        verbose_name=_("Interview|Decision"),
        max_length=15)
    decision_comment = models.TextField(
        _("Decision summary"),
        blank=True,
        null=True)

    class Meta:
        verbose_name = _("Interview")
        verbose_name_plural = _("Interviews")

    def get_absolute_url(self):
        return reverse('admission_interview_detail', args=[self.pk])

    def average_score(self):
        scores = [comment.score for comment in self.comments]
        if scores:
            return float(sum(scores)) / len(scores)
        return "-"

    def __str__(self):
        return smart_text("{} [{}]".format(self.applicant, self.date))


@python_2_unicode_compatible
class Comment(TimeStampedModel):
    interview = models.ForeignKey(
        Interview,
        verbose_name=_("Interview"),
        on_delete=models.PROTECT,
        related_name="comments")
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Interviewer"),
        on_delete=models.PROTECT,
        related_name="interview_comments")
    text = models.TextField(
        _("Text"),
        blank=True,
        null=True)
    score = models.SmallIntegerField(
        verbose_name=_("Score"),
        validators=[MinValueValidator(-2), MaxValueValidator(2)])

    class Meta:
        verbose_name = _("Comment")
        verbose_name_plural = _("Comments")
        unique_together = ("interview", "interviewer")

    def __str__(self):
        return smart_text("{} [{}]".format(self.interviewer.get_full_name(),
                                           self.interview.applicant.get_full_name()))

