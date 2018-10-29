# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime
import uuid
from collections import OrderedDict
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import query, Q
from django.urls import reverse
from django.core.validators import RegexValidator, MinValueValidator, \
    MaxValueValidator
from django.db import models, transaction
from django.utils import timezone, numberformat
from django.utils.encoding import python_2_unicode_compatible, smart_text
from django.utils.formats import date_format, time_format
from django.utils.safestring import mark_safe
from jsonfield import JSONField
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from multiselectfield import MultiSelectField
from post_office import mail
from post_office.models import Email, EmailTemplate, STATUS as EMAIL_STATUS
from post_office.utils import get_email_template

from core.db.models import GradeField
from core.models import City, University, LATEX_MARKDOWN_HTML_ENABLED
from learning.models import Venue
from learning.settings import PARTICIPANT_GROUPS, CENTER_FOUNDATION_YEAR, \
    DATE_FORMAT_RU
from learning.utils import get_current_term_pair
from users.models import User


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
    return timezone.now().year


class Campaign(models.Model):
    year = models.PositiveSmallIntegerField(
        _("Campaign|Year"),
        validators=[MinValueValidator(CENTER_FOUNDATION_YEAR)],
        default=current_year)
    city = models.ForeignKey(City, default=settings.DEFAULT_CITY_CODE,
                             verbose_name=_("City"),
                             on_delete=models.PROTECT)
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
    current = models.BooleanField(
        _("Current campaign"),
        help_text=_("Show in application form list"),
        default=False)
    application_ends_at = models.DateTimeField(
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

    def application_ends_at_local(self, tz=None):
        if not tz:
            tz = self.get_city_timezone()
        return timezone.localtime(self.application_ends_at, timezone=tz)

    def __str__(self):
        return smart_text(_("{}, {}").format(self.city.name, self.year))

    def display_short(self):
        return smart_text(_("{}, {}").format(self.city.abbr, self.year))

    def clean(self):
        if self.pk is None and self.current:
            msg = _("You can't set `current` on campaign creation")
            raise ValidationError(msg)
        if self.current:
            errors = []
            contests = Contest.objects.filter(campaign_id=self.pk,
                                              type=Contest.TYPE_TEST).count()
            if not contests:
                msg = _("Before mark campaign as `current` - add contests "
                        "for testing")
                errors.append(msg)
            if not self.template_name:
                errors.append(_("Empty template name"))
            else:
                from post_office.models import EmailTemplate
                tn = self.template_name
                if not EmailTemplate.objects.filter(name=tn).exists():
                    msg = _("Email template {} doesn't exist")
                    errors.append(msg.format(self.template_name))
            if not self.access_token:
                msg = _("Empty access token")
                errors.append(msg)
            if errors:
                msg = mark_safe("<br>".join(str(e) for e in errors))
                raise ValidationError(msg)


class ApplicantQuerySet(models.QuerySet):
    pass


class _ApplicantSubscribedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_unsubscribed=False)


ApplicantSubscribedManager = _ApplicantSubscribedManager.from_queryset(
    ApplicantQuerySet)


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
    FINAL_STATUSES = {
        ACCEPT,
        ACCEPT_IF,
        REJECTED_BY_INTERVIEW,
        VOLUNTEER
    }
    STUDY_PROGRAM_DS = "ds"
    STUDY_PROGRAM_CS = "cs"
    STUDY_PROGRAM_SE = "se"
    STUDY_PROGRAMS = (
        (STUDY_PROGRAM_DS, "Анализ данных"),
        (STUDY_PROGRAM_CS, "Современная информатика"),
        (STUDY_PROGRAM_SE, "Разработка ПО")
    )
    INFO_SOURCES = (
        ('uni', 'плакат/листовка в университете'),
        ('social_net', 'пост в соц. сетях'),
        ('friends', 'от друзей'),
        ('other', 'другое'),
        # Legacy options
        ('habr', 'Прочитал в статье на habr.ru'),
        ('club', 'Из CS клуба'),
        ('tandp', 'Теории и практики')
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
        choices=User.COURSES,
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
    has_job = models.NullBooleanField(
        _("Do you work?"),
        help_text=_("Applicant|has_job"))
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
    preferred_study_programs = MultiSelectField(
        _("Study program"),
        help_text=_("Applicant|study_program"),
        choices=STUDY_PROGRAMS,
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
    # Note: replace with m2m relation first if you need some statistics
    # based on field below
    where_did_you_learn = MultiSelectField(
        _("Where did you learn?"),
        help_text=_("Applicant|where_did_you_learn_about_cs_center"),
        choices=INFO_SOURCES)
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
    is_unsubscribed = models.BooleanField(
        _("Unsubscribed"),
        default=False,
        db_index=True,
        help_text=_("Unsubscribe from future notifications"))
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET(models.SET_NULL),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Applicant")
        verbose_name_plural = _("Applicants")
        unique_together = [('email', 'campaign')]

    objects = models.Manager()
    subscribed = ApplicantSubscribedManager()

    @transaction.atomic
    def save(self, **kwargs):
        created = self.pk is None
        super().save(**kwargs)
        if created:
            self._assign_testing()
        if self.is_unsubscribed:
            # Looking for other applicants with the same email and
            # unsubscribe them too.
            (Applicant.objects
             .filter(email=self.email)
             .exclude(pk=self.pk)
             .update(is_unsubscribed=True))

    def _assign_testing(self):
        testing = Test(applicant=self, status=Test.NEW)
        testing.save()

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


def validate_json_container(value):
    """
    Doesn't call if value is empty. This behavior checked in model clean method
    """
    if not isinstance(value, dict):
        raise ValidationError(
            "Serialized JSON should have dict as a container."
        )


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
    details = JSONField(
        verbose_name=_("Details"),
        load_kwargs={'object_pairs_hook': OrderedDict},
        blank=True,
        validators=[validate_json_container]
    )
    file = models.FileField(
        _("Assignments in pdf format"),
        blank=True,
        help_text=_("Make sure file does not include solutions due to "
                    "it visible with direct url link"),
        upload_to=contest_assignments_upload_to)

    class Meta:
        verbose_name = _("Contest")
        verbose_name_plural = _("Contests")

    def clean(self):
        if not self.details:
            self.details = {}

    def file_url(self):
        return self.file.url

    def __str__(self):
        return self.contest_id


class Test(TimeStampedModel):
    NEW = 'new'  # created
    REGISTERED = 'registered'  # registered in contest
    MANUAL = 'manual'  # manual score input
    STATUSES = (
        (NEW, _("New")),
        (REGISTERED, _("Registered in contest")),
        (MANUAL, _("Manual score input")),
    )
    applicant = models.OneToOneField(
        Applicant,
        verbose_name=_("Applicant"),
        on_delete=models.PROTECT,
        related_name="online_test")
    status = models.CharField(
        choices=STATUSES,
        default=NEW,
        verbose_name=_("Status"),
        max_length=15)
    details = JSONField(
        verbose_name=_("Details"),
        load_kwargs={'object_pairs_hook': OrderedDict},
        blank=True,
    )
    yandex_contest_id = models.CharField(
        _("Contest #ID"),
        help_text=_("Applicant|yandex_contest_id"),
        max_length=42,
        blank=True,
        null=True)
    contest_participant_id = models.IntegerField(
        help_text="Participant ID if user registered in Yandex Contest",
        editable=False,
        null=True,
        blank=True)
    contest_status_code = models.IntegerField(
        "Yandex API Response",
        editable=False,
        null=True,
        blank=True)
    score = models.PositiveSmallIntegerField(
        verbose_name=_("Score"), null=True, blank=True)

    class Meta:
        verbose_name = _("Testing")
        verbose_name_plural = _("Testings")

    def __str__(self):
        """ Import/export get repr before instance created in db."""
        if self.applicant_id:
            return self.applicant.get_full_name()
        else:
            return smart_text(self.score)

    def score_display(self):
        return self.score if self.score is not None else "-"

    def compute_contest_id(self):
        """
        Returns contest id based on applicant id and existing contest records.
        """
        contests = list(Contest.objects
                        .filter(campaign_id=self.applicant.campaign_id,
                                type=Contest.TYPE_TEST)
                        .values_list("contest_id", flat=True)
                        .order_by("contest_id"))
        if contests:
            contest_index = self.applicant.id % len(contests)
            return contests[contest_index]

    def save(self, **kwargs):
        created = self.pk is None
        if created and not self.yandex_contest_id:
            contest_id = self.compute_contest_id()
            if contest_id:
                self.yandex_contest_id = contest_id
        super().save(**kwargs)


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
    score = GradeField(
        verbose_name=_("Score"),
        # Avoid loading empty values with admin interface
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

    def score_display(self):
        return self.score if self.score is not None else "-"


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
        return timezone.localtime(self.date, timezone=tz)

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city_timezone()

    @property
    def city_aware_field_name(self):
        # TODO: store venue in this model?
        return self.__class__.applicant.field.name

    def clean(self):
        if self.status != self.APPROVAL and not self.date:
            raise ValidationError("You can't change status without date set up")

    def get_absolute_url(self):
        return reverse('admission:interview_detail', args=[self.pk])

    def in_transition_state(self):
        return self.status in self.TRANSITION_STATUSES

    @property
    def average_score(self):
        # `_average_score` can be calculated with query annotation to improve
        # performance
        if hasattr(self, "_average_score"):
            return self._average_score
        scores = [comment.score for comment in self.comments.all()]
        if scores:
            self._average_score = float(sum(scores)) / len(scores)
            return self._average_score

    def get_average_score_display(self, decimal_pos=2):
        return numberformat.format(self.average_score, ".", decimal_pos)

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
    # Extract this value from interview datetime before sending notification
    # to applicant
    WITH_ASSIGNMENTS_TIMEDELTA = datetime.timedelta(minutes=30)

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
    campaign = models.ForeignKey(
        Campaign,
        verbose_name=_("Campaign"),
        on_delete=models.CASCADE,
        blank=True,
        related_name="interview_streams")

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
        if self.venue_id and not self.campaign_id:
            try:
                self.campaign = Campaign.objects.get(current=True,
                                                     city_id=self.venue.city_id)
            except Campaign.DoesNotExist:
                msg = f"No current campaign provided for venue {self.venue}"
                raise ValidationError(msg)
        # TODO: Divisible or not?


class InterviewSlotQuerySet(query.QuerySet):
    def lock(self, slot, interview):
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

    @property
    def is_empty(self):
        return not bool(self.interview_id)


class InterviewInvitationQuerySet(query.QuerySet):
    def for_applicant(self, applicant):
        """Returns last active invitation for requested user"""
        today = timezone.now()
        return (self.filter(Q(expired_at__gt=today) |
                            Q(expired_at__isnull=True))
                    .filter(applicant=applicant)
                .order_by("-pk")
                .first())


class InterviewInvitation(TimeStampedModel):
    ONE_STREAM_EMAIL_TEMPLATE = "admission-interview-invitation"

    applicant = models.ForeignKey(
        Applicant,
        verbose_name=_("Applicant"),
        on_delete=models.PROTECT,
        related_name="interview_invitations")
    streams = models.ManyToManyField(
        InterviewStream,
        verbose_name=_("Interview streams"),
        related_name="interview_invitations")
    secret_code = models.UUIDField(
        verbose_name=_("Secret code"),
        default=uuid.uuid4)
    expired_at = models.DateTimeField(
        _("Expired at"),
        # FIXME: get timezone from applicant
        help_text=_("Time in UTC since information about city timezone "
                    "stored in m2m relationship"))
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

    def __unicode__(self):
        return str(self.applicant)

    def __str__(self):
        return self.__unicode__()

    @property
    def is_expired(self):
        return timezone.now() >= self.expired_at

    @property
    def is_accepted(self):
        return bool(self.interview_id)

    def get_absolute_url(self):
        return reverse("admission:interview_appointment", kwargs={
            "year": self.applicant.campaign.year,
            "secret_code": str(self.secret_code).replace("-", "")
        })

    def send_email(self, stream=None, uri_builder=None):
        # XXX: Create data migration if you changed template name
        template_name = "admission-interview-invitation-n-streams"
        if uri_builder:
            secret_link = uri_builder(self.get_absolute_url())
        else:
            secret_link = "https://compscicenter.ru{}".format(
                self.get_absolute_url())
        context = {
            "SECRET_LINK": secret_link,
        }
        if stream:
            template_name = self.ONE_STREAM_EMAIL_TEMPLATE
            context.update({
                "SUBJECT_CITY": stream.venue.city.name,
                "SHORT_DATE": date_format(stream.date, "d E"),
                "OFFICE_TITLE": stream.venue.name,
                "WITH_ASSIGNMENTS": stream.with_assignments,
                "DIRECTIONS": stream.venue.directions,
            })
        return mail.send(
            [self.applicant.email],
            # TODO: move to settings
            sender='CS центр <info@compscicenter.ru>',
            template=template_name,
            context=context,
            # Render on delivery, we have no really big amount of
            # emails to think about saving CPU time
            render_on_delivery=True,
            backend='ses',
        )
