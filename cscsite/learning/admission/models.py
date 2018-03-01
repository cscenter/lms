# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime
import uuid
from collections import OrderedDict
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import query, Q
from django.templatetags.tz import datetimeobject
from django.urls import reverse
from django.core.validators import RegexValidator, MinValueValidator, \
    MaxValueValidator
from django.db import models
from django.utils.encoding import python_2_unicode_compatible, smart_text
from django.utils.formats import date_format, time_format
from django.utils.timezone import now, make_aware, localtime
from jsonfield import JSONField
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from post_office import mail
from post_office.models import Email, EmailTemplate, STATUS as EMAIL_STATUS
from post_office.utils import get_email_template

from core.models import City, University, LATEX_MARKDOWN_HTML_ENABLED
from learning.models import Venue
from learning.settings import PARTICIPANT_GROUPS, CENTER_FOUNDATION_YEAR
from learning.utils import get_current_term_pair
from users.models import CSCUser


WITH_ASSIGNMENTS_TEXT = """
Сперва мы предложим Вам решить несколько задач в течение получаса, а само 
собеседование займёт ещё около 30 минут. На нём мы обсудим Вашу мотивацию 
поступления в центр, существующий опыт и успехи в учёбе. Возможно, в разговоре 
мы затронем также результаты экзамена, попросим решить какие-то задачи по 
математике и программированию. Специально готовиться к собеседованию не стоит: 
приходите с теми знаниями, которые есть, а вот про мотивацию подумайте, 
пожалуйста, заранее. Собеседование проведут кураторы и преподаватели центра."""


def current_year():
    # Don't care about inaccuracy and use UTC timezone here
    return now().year


@python_2_unicode_compatible
class Campaign(models.Model):
    year = models.PositiveSmallIntegerField(
        _("Campaign|Year"),
        validators=[MinValueValidator(CENTER_FOUNDATION_YEAR)],
        default=current_year)
    city = models.ForeignKey(City, default=settings.DEFAULT_CITY_CODE,
                             verbose_name=_("City"))
    online_test_max_score = models.SmallIntegerField(
        _("Campaign|Test_max_score"))
    online_test_passing_score = models.SmallIntegerField(
        _("Campaign|Test_passing_score"),
        help_text=_("Campaign|Test_passing_score-help"))
    exam_max_score = models.SmallIntegerField(
        _("Campaign|Exam_max_score"))
    exam_passing_score = models.SmallIntegerField(
        _("Campaign|Exam_passing_score"),
        help_text=_("Campaign|Exam_passing_score-help"))
    current = models.BooleanField(_("Current campaign"), default=False)
    application_ends_at = models.DateField(
        _("Application Ends At"),
        help_text=_("Last day for submitting application"))
    access_token = models.CharField(
        _("Access Token"),
        help_text=_("Yandex.Contest Access Token"),
        max_length=255,
        blank=True)
    refresh_token = models.CharField(
        _("Refresh Token"),
        help_text=_("Yandex.Contest Refresh Token"),
        max_length=255,
        blank=True)
    template_name = models.CharField(
        _("Template Name"),
        help_text=_("Template name for invitation email message"),
        max_length=255,
        blank=True)

    class Meta:
        verbose_name = _("Campaign")
        verbose_name_plural = _("Campaigns")

    def get_city_timezone(self):
        return settings.TIME_ZONES[self.city_id]

    @property
    def city_aware_field_name(self):
        return self.__class__.city.field.name

    def __str__(self):
        return smart_text(_("{}, {}").format(self.city.name, self.year))

    def display_short(self):
        return smart_text(_("{}, {}").format(self.city.abbr, self.year))


@python_2_unicode_compatible
class Applicant(TimeStampedModel):
    REJECTED_BY_TEST = 'rejected_test'
    PERMIT_TO_EXAM = 'permit_to_exam'
    REJECTED_BY_EXAM = 'rejected_exam'
    REJECTED_BY_CHEATING = 'rejected_cheating'
    # TODO: rename interview codes here and in DB. Replace values type?
    INTERVIEW_TOBE_SCHEDULED = 'interview_phase'  # permitted to interview
    INTERVIEW_SCHEDULED = 'interview_assigned'
    INTERVIEW_COMPLETED = 'interview_completed'
    REJECTED_BY_INTERVIEW = 'rejected_interview'
    PENDING = 'pending'
    ACCEPT = 'accept'
    ACCEPT_IF = 'accept_if'
    VOLUNTEER = 'volunteer'
    THEY_REFUSED = 'they_refused'
    STATUS = (
        (REJECTED_BY_TEST, _('Rejected by test')),
        (PERMIT_TO_EXAM, _('Permitted to the exam')),
        (REJECTED_BY_EXAM, _('Rejected by exam')),
        (REJECTED_BY_CHEATING, _('Cheating')),
        (PENDING, _('Pending')),
        (INTERVIEW_TOBE_SCHEDULED, _('Can be interviewed')),
        (INTERVIEW_SCHEDULED, _('Interview assigned')),
        (INTERVIEW_COMPLETED, _('Interview completed')),
        (REJECTED_BY_INTERVIEW, _('Rejected by interview')),
        (ACCEPT, _('Accept')),
        (ACCEPT_IF, _('Accept with condition')),
        (VOLUNTEER, _("Applicant|Volunteer")),
        (THEY_REFUSED, _("He or she refused")),
    )

    campaign = models.ForeignKey(
        Campaign,
        verbose_name=_("Applicant|Campaign"),
        on_delete=models.PROTECT,
        related_name="applicants")
    first_name = models.CharField(_("First name"), max_length=255)
    surname = models.CharField(_("Surname"), max_length=255)
    patronymic = models.CharField(_("Patronymic"), max_length=255)
    email = models.EmailField(
        _("Email"),
        help_text=_("Applicant|email"))
    phone = models.CharField(
        _("Contact phone"),
        max_length=42,
        help_text=_("Applicant|phone"))
    stepic_id = models.PositiveIntegerField(
        _("Stepik ID"),
        help_text=_("Applicant|stepic_id"),
        blank=True,
        null=True)
    yandex_id = models.CharField(
        _("Yandex ID"),
        max_length=80,
        help_text=_("Applicant|yandex_id"),
        null=True,
        blank=True)
    yandex_id_normalize = models.CharField(
        _("Yandex ID normalisation"),
        max_length=80,
        help_text=_("Applicant|yandex_id_normalization"),
        null=True,
        blank=True)
    github_id = models.CharField(
        _("Github ID"),
        max_length=255,
        help_text=_("Applicant|github_id"),
        null=True,
        blank=True)

    university = models.ForeignKey(
        University,
        verbose_name=_("Applicant|University"),
        on_delete=models.PROTECT,
        related_name="applicants")
    university2 = models.CharField(
        _("University_legacy"),
        help_text=_("Applicant|university_legacy"),
        max_length=255,
        null=True,
        blank=True)
    university_other = models.CharField(
        _("University (Other)"),
        help_text=_("Applicant|university_other"),
        max_length=255,
        null=True,
        blank=True)
    faculty = models.TextField(
        _("Faculty"),
        help_text=_("Applicant|faculty"))
    course = models.CharField(
        _("Course"),
        choices=CSCUser.COURSES,
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
    preferred_study_programs_dm_note = models.TextField(
        _("Study program (DM note)"),
        help_text=_("Applicant|study_program_dm"),
        null=True,
        blank=True)
    preferred_study_programs_se_note = models.TextField(
        _("Study program (SE note)"),
        help_text=_("Applicant|study_program_se"),
        null=True,
        blank=True)
    preferred_study_programs_cs_note = models.TextField(
        _("Study program (CS note)"),
        help_text=_("Applicant|study_program_cs"),
        null=True,
        blank=True)
    where_did_you_learn = models.TextField(
        _("Where did you learn?"),
        help_text=_("Applicant|where_did_you_learn_about_cs_center"))
    # Note: If in next year where_did_you_learn will stay TextField, remove
    # field below (merge there values on form level)
    where_did_you_learn_other = models.CharField(
        _("Where did you learn? (other)"),
        max_length=255,
        null=True,
        blank=True)
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
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET(models.SET_NULL),
        null=True,
        blank=True,
    )
    uuid = models.UUIDField(editable=False, null=True, blank=True)
    contest_id = models.IntegerField(
        _("Yandex.Contest ID"),
        null=True,
        blank=True)
    participant_id = models.IntegerField(
        _("Participant ID"),
        help_text=_("Participant ID if user registered in Yandex Contest"),
        null=True,
        blank=True)
    status_code = models.IntegerField(
        "Yandex API Response",
        editable=False,
        null=True,
        blank=True)

    class Meta:
        verbose_name = _("Applicant")
        verbose_name_plural = _("Applicants")
        unique_together = [('email', 'campaign')]

    def save(self, **kwargs):
        created = self.pk is None
        super().save(**kwargs)
        self._set_contest_id(created)

    def _set_contest_id(self, created):
        if not created:
            return False
        contests = list(Contest.objects
                        .filter(campaign_id=self.campaign_id,
                                type=Contest.TYPE_TEST)
                        .values_list("contest_id", flat=True)
                        .order_by("contest_id"))
        if contests:
            contest_index = self.pk % len(contests)
            self.contest_id = contests[contest_index]
            (Applicant.objects
             .filter(pk=self.pk)
             .update(contest_id=self.contest_id))

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city_timezone()

    @property
    def city_aware_field_name(self):
        return self.__class__.campaign.field.name

    def get_full_name(self):
        parts = [self.surname, self.first_name, self.patronymic]
        return smart_text(" ".join(part for part in parts if part).strip())

    def clean(self):
        if self.yandex_id:
            self.yandex_id_normalize = self.yandex_id.lower().replace('-', '.')

    @classmethod
    def get_name_by_status_code(cls, code):
        for status_code, status_name in cls.STATUS:
            if status_code == code:
                return status_name
        return ""

    def get_absolute_url(self):
        return reverse('admission:applicant_detail', args=[self.pk])

    def __str__(self):
        if self.campaign_id:
            return smart_text(
                "{} [{}]".format(self.get_full_name(), self.campaign))
        else:
            return smart_text(self.get_full_name())

    def interview_successfull(self):
        """Successfully pass interview and ready to become student center"""
        return self.status in [self.ACCEPT, self.ACCEPT_IF, self.VOLUNTEER]


def contest_assignments_upload_to(instance, filename):
    # TODO: Can be visible for unauthenticated. Is it ok?
    return instance.FILE_PATH_TEMPLATE.format(
        contest_id=instance.contest_id,
        filename=filename)


class Contest(models.Model):

    FILE_PATH_TEMPLATE = "contest/{contest_id}/assignments/{filename}"
    TYPE_TEST = 1
    TYPE_EXAM = 2
    TYPES = (
        (TYPE_TEST, _("Testing")),
        (TYPE_EXAM, _("Exam")),
    )
    campaign = models.ForeignKey(
        Campaign,
        verbose_name=_("Contest|Campaign"),
        on_delete=models.PROTECT,
        related_name="contests")
    type = models.IntegerField(
        _("Type"),
        choices=TYPES)
    contest_id = models.CharField(
        _("Contest #ID"),
        help_text=_("Applicant|yandex_contest_id"),
        max_length=42,
        blank=True,
        null=True)

    file = models.FileField(
        _("Assignments in pdf format"),
        blank=True,
        help_text=_("Make sure file does not include solutions due to "
                    "it visible with direct url link"),
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
        verbose_name=_("Details"),
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
    score = models.PositiveSmallIntegerField(
        verbose_name=_("Score"))

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
        verbose_name=_("Details"),
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
        verbose_name=_("Score"),
        null=True)

    class Meta:
        verbose_name = _("Exam")
        verbose_name_plural = _("Exams")

    def is_imported(self):
        """NULL value on DB level means we only created model for exam and set
        contest id, but results never been imported from contest."""
        return self.score is not None

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
    solution = models.TextField(
        _("Assignment solution"),
        help_text=_("TeX support"),
        null=True,
        blank=True)

    class Meta:
        verbose_name = _("Interview assignment")
        verbose_name_plural = _("Interview assignments")

    def __str__(self):
        return smart_text(self.name)


@python_2_unicode_compatible
class Interview(TimeStampedModel):
    APPROVAL = 'approval'
    APPROVED = 'waiting'
    DEFERRED = 'deferred'
    CANCELED = 'canceled'
    COMPLETED = 'completed'
    STATUSES = (
        (APPROVAL, _('Approval')),
        (DEFERRED, _('Deferred')),
        (CANCELED, _('Canceled')),
        (APPROVED, _('Approved')),
        (COMPLETED, _('Completed')),
    )
    TRANSITION_STATUSES = [DEFERRED, CANCELED, APPROVAL]
    REMINDER_TEMPLATE = "admission-interview-reminder"
    FEEDBACK_TEMPLATE = "admission-interview-feedback"

    date = models.DateTimeField(_("When"))
    applicant = models.OneToOneField(
        Applicant,
        verbose_name=_("Applicant"),
        on_delete=models.PROTECT,
        related_name="interview")
    interviewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Interview|Interviewers"),
        limit_choices_to={'groups__pk': PARTICIPANT_GROUPS.INTERVIEWER})

    assignments = models.ManyToManyField(
        'InterviewAssignment',
        verbose_name=_("Interview|Assignments"),
        blank=True)

    status = models.CharField(
        choices=STATUSES,
        default=APPROVAL,
        verbose_name=_("Interview|Status"),
        max_length=15)
    note = models.TextField(
        _("Note"),
        blank=True,
        null=True)

    class Meta:
        verbose_name = _("Interview")
        verbose_name_plural = _("Interviews")

    def date_local(self, tz=None):
        if not tz:
            tz = self.get_city_timezone()
        return localtime(self.date, timezone=tz)

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city_timezone()

    @property
    def city_aware_field_name(self):
        return self.__class__.applicant.field.name

    def clean(self):
        if self.status != self.APPROVAL and not self.date:
            raise ValidationError("You can't change status without date set up")

    def get_absolute_url(self):
        return reverse('admission:interview_detail', args=[self.pk])

    def in_transition_state(self):
        return self.status in self.TRANSITION_STATUSES

    def average_score(self):
        scores = [comment.score for comment in self.comments.all()]
        if scores:
            return float(sum(scores)) / len(scores)

    def __str__(self):
        return smart_text(self.applicant)

    def delete_reminder(self):
        try:
            template = get_email_template(Interview.REMINDER_TEMPLATE)
            (Email.objects
             .filter(template=template, to=self.applicant.email)
             .exclude(status=EMAIL_STATUS.sent)
             .delete())
        except EmailTemplate.DoesNotExist:
            pass

    def delete_feedback(self):
        try:
            template = get_email_template(Interview.FEEDBACK_TEMPLATE)
            (Email.objects
             .filter(template=template, to=self.applicant.email)
             .exclude(status=EMAIL_STATUS.sent)
             .delete())
        except EmailTemplate.DoesNotExist:
            pass


@python_2_unicode_compatible
class Comment(TimeStampedModel):
    MIN_SCORE = -2
    MAX_SCORE = 2
    UNREACHABLE_COMMENT_SCORE = MIN_SCORE - 1

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
        validators=[MinValueValidator(MIN_SCORE), MaxValueValidator(MAX_SCORE)])

    class Meta:
        verbose_name = _("Comment")
        verbose_name_plural = _("Comments")
        unique_together = ("interview", "interviewer")

    def __str__(self):
        return smart_text("{} [{}]".format(self.interviewer.get_full_name(),
                                           self.interview.applicant.get_full_name()))


class InterviewStream(TimeStampedModel):
    date = models.DateField(_("Interview day"))
    start_at = models.TimeField(_("Period start"))
    end_at = models.TimeField(_("Period end"))
    duration = models.IntegerField(
        _("Slot duration"),
        validators=[MinValueValidator(10)],
        default=30)
    # TODO: do not change if some slots already was taken
    venue = models.ForeignKey(
        Venue,
        verbose_name=_("Interview venue"),
        on_delete=models.PROTECT,
        related_name="streams")
    with_assignments = models.BooleanField(
        _("Has assignments"),
        help_text=_("Based on this flag, student should arrive 30 min "
                    "before or not"))
    interviewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Interview|Interviewers"),
        limit_choices_to={'groups__pk': PARTICIPANT_GROUPS.INTERVIEWER})

    class Meta:
        verbose_name = _("Interview stream")
        verbose_name_plural = _("Interview streams")

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        # self.venue.get_city_timezone()
        return next_in_city_aware_mro.get_city_timezone()

    @property
    def city_aware_field_name(self):
        return self.__class__.venue.field.name

    def __str__(self):
        return "{}, {}-{}".format(
            date_format(self.date, settings.DATE_FORMAT),
            time_format(self.start_at),
            time_format(self.end_at))

    def clean(self):
        if self.start_at and self.end_at and self.duration:
            self.start_at = self.start_at.replace(second=0, microsecond=0)
            self.end_at = self.end_at.replace(second=0, microsecond=0)
            start_at = datetime.timedelta(hours=self.start_at.hour,
                                          minutes=self.start_at.minute)
            end_at = datetime.timedelta(hours=self.end_at.hour,
                                        minutes=self.end_at.minute)
            diff = (end_at - start_at).total_seconds() / 60
            if diff < self.duration:
                raise ValidationError(
                    _("Stream duration can't be less than slot duration"))
        # TODO: Divisible or not?


class InterviewSlotQuerySet(query.QuerySet):
    def take(self, slot, interview):
        """Try to fill interview slot in a CAS manner"""
        return (self.filter(pk=slot.pk,
                            interview_id__isnull=True)
                .update(interview_id=interview.pk))


class InterviewSlot(TimeStampedModel):
    interview = models.OneToOneField(
        Interview,
        verbose_name=_("Interview"),
        on_delete=models.SET_NULL,
        related_name="slot",
        null=True,
        blank=True)
    start_at = models.TimeField(_("Interview start"))
    end_at = models.TimeField(_("Interview end"))
    stream = models.ForeignKey(
        InterviewStream,
        verbose_name=_("Interview stream"),
        on_delete=models.PROTECT,
        related_name="slots")

    class Meta:
        ordering = ['start_at']
        verbose_name = _("Interview slot")
        verbose_name_plural = _("Interview slots")

    objects = InterviewSlotQuerySet.as_manager()

    def __str__(self):
        return time_format(self.start_at)


class InterviewInvitationQuerySet(query.QuerySet):
    def for_applicant(self, applicant):
        """Returns last active invitation for requested user"""
        today = now()
        return (self.filter(Q(expired_at__gt=today) | Q(expired_at__isnull=True,
                                                        date__gte=today.date()))
                    .filter(applicant=applicant)
                .order_by("-pk")
                .first())


class InterviewInvitation(TimeStampedModel):
    EMAIL_TEMPLATE = "admission-interview-invitation"

    applicant = models.ForeignKey(
        Applicant,
        verbose_name=_("Applicant"),
        on_delete=models.PROTECT,
        related_name="interview_invitations")
    stream = models.ForeignKey(
        InterviewStream,
        verbose_name=_("Interview stream"),
        on_delete=models.PROTECT,
        related_name="interview_invitations")
    secret_code = models.UUIDField(
        verbose_name=_("Secret code"),
        default=uuid.uuid4)
    expired_at = models.DateTimeField(_("Expired at"))
    date = models.DateField(
        _("Estimated interview day"))
    interview = models.ForeignKey(
        Interview,
        verbose_name=_("Interview"),
        on_delete=models.CASCADE,
        related_name="invitations",
        null=True,
        blank=True)

    class Meta:
        verbose_name = _("Interview invitation")
        verbose_name_plural = _("Interview invitations")

    objects = InterviewInvitationQuerySet.as_manager()

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        # self.stream.venue.get_city_timezone()
        return next_in_city_aware_mro.get_city_timezone()

    def get_city(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city()

    @property
    def city_aware_field_name(self):
        return self.__class__.stream.field.name

    def __str__(self):
        return str(self.date)

    @property
    def is_expired(self):
        return now() >= self.expired_at

    @property
    def is_accepted(self):
        return bool(self.interview_id)

    def get_absolute_url(self):
        return reverse("admission:interview_appointment", kwargs={
            "date": self.date.strftime('%d.%m.%Y'),
            "secret_code": str(self.secret_code).replace("-", "")
        })

    def send_email(self, uri_builder=None):
        if uri_builder:
            secret_link = uri_builder(self.get_absolute_url())
        else:
            secret_link = "https://compscicenter.ru{}".format(
                self.get_absolute_url())
        context = {
            "SUBJECT_CITY": self.stream.venue.city.name,
            "SHORT_DATE": date_format(self.stream.date, "d E"),
            "OFFICE_TITLE": self.stream.venue.name,
            "WITH_ASSIGNMENTS": self.stream.with_assignments,
            "SECRET_LINK": secret_link,
            "DIRECTIONS": self.stream.venue.directions,
        }
        return mail.send(
            [self.applicant.email],
            sender='info@compscicenter.ru',
            template=self.EMAIL_TEMPLATE,
            context=context,
            # Render on delivery, we have no really big amount of
            # emails to think about saving CPU time
            render_on_delivery=True,
            backend='ses',
        )
