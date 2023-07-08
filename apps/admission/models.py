import datetime
import string
import uuid
from decimal import Decimal
from typing import Any, ClassVar, NamedTuple, Optional, Type, Union

from django.utils.functional import cached_property
from djchoices import DjangoChoices
from model_utils.models import TimeStampedModel
from multiselectfield import MultiSelectField
from post_office.models import EmailTemplate

from django.conf import settings
from django.core import checks
from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Count, OuterRef, Q, Subquery, Value, query
from django.db.models.functions import Coalesce
from django.utils import numberformat, timezone
from django.utils.encoding import force_bytes, smart_str
from django.utils.formats import date_format, time_format
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from admission.constants import (
    ApplicantStatuses,
    ChallengeStatuses,
    ContestTypes,
    DefaultInterviewRatingSystem,
    InterviewFormats,
    InterviewInvitationStatuses,
    InterviewSections,
    YandexDataSchoolInterviewRatingSystem,
)
from admission.utils import get_next_process, slot_range
from api.services import generate_hash, generate_random_string
from api.settings import DIGEST_MAX_LENGTH
from core.db.fields import ScoreField
from core.db.mixins import DerivableFieldsMixin
from core.models import Branch, Location, TimestampedModel
from core.timezone import TimezoneAwareMixin
from core.timezone.fields import TimezoneAwareDateTimeField
from core.urls import reverse
from core.utils import normalize_yandex_login
from files.models import ConfigurableStorageFileField
from files.storage import private_storage
from grading.api.yandex_contest import Error as YandexContestError
from grading.api.yandex_contest import RegisterStatus
from learning.settings import AcademicDegreeLevels
from lms.settings.base import YDS_SITE_ID
from notifications.base_models import EmailAddressSuspension
from users.constants import Roles


def current_year():
    # Don't care about inaccuracy and use UTC timezone here
    return timezone.now().year


def validate_email_template_name(value):
    if value and not EmailTemplate.objects.filter(name=value).exists():
        raise ValidationError(
            _("Email template with name `%(template_name)s` doesn't exist"),
            params={"template_name": value},
        )


class Campaign(TimezoneAwareMixin, models.Model):
    TIMEZONE_AWARE_FIELD_NAME = "branch"

    year = models.PositiveSmallIntegerField(
        _("Campaign|Year"), validators=[MinValueValidator(2000)], default=current_year
    )
    branch = models.ForeignKey(
        Branch,
        verbose_name=_("Branch"),
        related_name="campaigns",
        on_delete=models.PROTECT,
    )
    current = models.BooleanField(
        _("Current Admission"),
        help_text=_(
            "You can mark campaign as current only after adding contests for testing"
        ),
        default=False,
    )
    order = models.PositiveIntegerField(verbose_name=_("Order"), default=1000)
    online_test_max_score = models.SmallIntegerField(_("Campaign|Test_max_score"))
    online_test_passing_score = models.SmallIntegerField(
        _("Campaign|Test_passing_score"),
        help_text=_("Campaign|Test_passing_score-help"),
    )
    exam_max_score = models.SmallIntegerField(
        _("Campaign|Exam_max_score"), null=True, blank=True
    )
    exam_passing_score = models.SmallIntegerField(
        _("Campaign|Exam_passing_score"),
        help_text=_("Campaign|Exam_passing_score-help"),
        null=True,
        blank=True,
    )
    application_starts_at = TimezoneAwareDateTimeField(_("Application Starts on"))
    application_ends_at = TimezoneAwareDateTimeField(
        _("Application Ends on"), help_text=_("Last day for submitting application")
    )
    confirmation_ends_at = TimezoneAwareDateTimeField(
        _("Confirmation Ends on"),
        help_text=_("Deadline for accepting invitation to create student profile"),
        blank=True,
        null=True,
    )
    access_token = models.CharField(
        _("Access Token"),
        help_text=_("Yandex.Contest Access Token"),
        max_length=255,
        blank=True,
    )
    refresh_token = models.CharField(
        _("Refresh Token"),
        help_text=_("Yandex.Contest Refresh Token"),
        max_length=255,
        blank=True,
    )
    # FIXME: factory boy allows to save blank values for template names :<
    template_registration = models.CharField(
        _("Registration Template"),
        help_text=_("Template name for contest registration email"),
        validators=[validate_email_template_name],
        max_length=255,
    )
    template_exam_invitation = models.CharField(
        _("Exam Invitation Email Template"),
        help_text=_("Template name for the exam registration email"),
        validators=[validate_email_template_name],
        blank=True,
        max_length=255,
    )
    template_appointment = models.CharField(
        _("Invitation Template"),
        help_text=_("Template name for interview invitation email"),
        validators=[validate_email_template_name],
        max_length=255,
    )
    template_interview_feedback = models.ForeignKey(
        EmailTemplate,
        verbose_name=_("Interview Feedback Template"),
        help_text=_(
            "Leave blank if there is no need to send a feedback email. "
            "Email will be sent at the time of interview status change, "
            "but not earlier than 21:00 of the day of the interview"
        ),
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )

    class Meta:
        app_label = "admission"
        verbose_name = _("Campaign")
        verbose_name_plural = _("Campaigns")

    def __str__(self):
        return smart_str(_("{}, {}").format(self.branch.name, self.year))

    def application_starts_at_local(self, tz=None):
        if not tz:
            tz = self.get_timezone()
        return timezone.localtime(self.application_starts_at, timezone=tz)

    def application_ends_at_local(self, tz=None):
        if not tz:
            tz = self.get_timezone()
        return timezone.localtime(self.application_ends_at, timezone=tz)

    def clean(self):
        if self.pk is None and self.current:
            msg = _("You can't set `current` on campaign creation")
            raise ValidationError(msg)
        errors = {}
        if self.current:
            contests = Contest.objects.filter(
                campaign_id=self.pk, type=Contest.TYPE_TEST
            ).count()
            if not contests:
                msg = _(
                    "Before mark campaign as `current` - add contests " "for testing"
                )
                errors["__all__"] = msg
            if not self.access_token:
                errors["access_token"] = _("Empty access token")
        if errors:
            raise ValidationError(errors)

    @classmethod
    def with_open_registration(cls):
        """Returns campaigns marked as `current` with open registration form"""
        today = timezone.now()
        return cls.objects.filter(
            current=True,
            application_starts_at__lte=today,
            application_ends_at__gt=today,
        ).select_related("branch")

    @property
    def is_active(self):
        today = timezone.now()
        return self.current and today <= self.application_ends_at


# TODO: remove after migrating to core.University
class University(models.Model):
    """
    Some universities are interesting for statistics. To avoid typos,
    different word order, abbreviations, letter case and
    many more things which could prevent accurately aggregate data, store
    target universities for each branch in this model.
    """

    name = models.CharField(
        _("University"), max_length=255, help_text=_("Perhaps also the faculty.")
    )
    abbr = models.CharField(
        _("University abbreviation"), max_length=100, blank=True, null=True
    )
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)
    branch = models.ForeignKey(
        Branch,
        verbose_name=_("Branch"),
        related_name="+",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
    )

    class Meta:
        app_label = "admission"
        verbose_name = _("University")
        verbose_name_plural = _("Universities")

    def __str__(self):
        return smart_str(self.name)


class ApplicantQuerySet(models.QuerySet):
    pass


class _ApplicantSubscribedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_unsubscribed=False)


ApplicantSubscribedManager = _ApplicantSubscribedManager.from_queryset(
    ApplicantQuerySet
)


class Applicant(TimezoneAwareMixin, TimeStampedModel, EmailAddressSuspension):
    TIMEZONE_AWARE_FIELD_NAME = "campaign"

    # TODO: access applicant statuses with .STATUS.<code> instead
    REJECTED_BY_TEST = ApplicantStatuses.REJECTED_BY_TEST
    PERMIT_TO_EXAM = ApplicantStatuses.PERMIT_TO_EXAM
    REJECTED_BY_EXAM = ApplicantStatuses.REJECTED_BY_EXAM
    REJECTED_BY_EXAM_CHEATING = ApplicantStatuses.REJECTED_BY_EXAM_CHEATING
    REJECTED_BY_CHEATING = ApplicantStatuses.REJECTED_BY_CHEATING
    # TODO: rename interview codes here and in DB. Replace values type?
    INTERVIEW_TOBE_SCHEDULED = (
        ApplicantStatuses.INTERVIEW_TOBE_SCHEDULED
    )  # permitted to interview
    # FIXME: remove
    INTERVIEW_SCHEDULED = ApplicantStatuses.INTERVIEW_SCHEDULED
    INTERVIEW_COMPLETED = ApplicantStatuses.INTERVIEW_COMPLETED
    REJECTED_BY_INTERVIEW = ApplicantStatuses.REJECTED_BY_INTERVIEW
    PENDING = ApplicantStatuses.PENDING
    ACCEPT = ApplicantStatuses.ACCEPT
    ACCEPT_PAID = ApplicantStatuses.ACCEPT_PAID
    WAITING_FOR_PAYMENT = ApplicantStatuses.WAITING_FOR_PAYMENT
    ACCEPT_IF = ApplicantStatuses.ACCEPT_IF
    VOLUNTEER = ApplicantStatuses.VOLUNTEER
    THEY_REFUSED = ApplicantStatuses.THEY_REFUSED

    STATUS = ApplicantStatuses.choices
    # One of the statuses below could be set after interviewing
    INTERVIEW_RESULTS = {
        ACCEPT,
        ACCEPT_PAID,
        ACCEPT_IF,
        REJECTED_BY_INTERVIEW,
        ApplicantStatuses.REJECTED_BY_INTERVIEW_WITH_BONUS,
        VOLUNTEER,
        WAITING_FOR_PAYMENT,
    }
    # Successful final statuses after interview stage
    ACCEPT_STATUSES = {
        ACCEPT,
        ACCEPT_PAID,
        ACCEPT_IF,
        VOLUNTEER,
        WAITING_FOR_PAYMENT,
    }
    STUDY_PROGRAM_DS = "ds"
    STUDY_PROGRAM_CS = "cs"
    STUDY_PROGRAM_SE = "se"
    STUDY_PROGRAM_ROBOTICS = "robotics"
    STUDY_PROGRAMS = (
        (STUDY_PROGRAM_CS, "Computer Science (Современная информатика)"),
        (STUDY_PROGRAM_DS, "Data Science (Анализ данных)"),
        (STUDY_PROGRAM_SE, "Software Engineering (Разработка ПО)"),
        (STUDY_PROGRAM_ROBOTICS, "Robotics (Роботы)"),
    )
    INFO_SOURCES = (
        ("uni", "плакат/листовка в университете"),
        ("social_net", "пост в соц. сетях"),
        ("ambassador", "от амбассадора Yandex U-Team"),
        ("friends", "от друзей"),
        ("other", "другое"),
        # Legacy options
        ("habr", "Прочитал в статье на habr.ru"),
        ("club", "Из CS клуба"),
        ("tandp", "Теории и практики"),
    )

    campaign = models.ForeignKey(
        Campaign,
        verbose_name=_("Applicant|Campaign"),
        on_delete=models.PROTECT,
        related_name="applicants",
    )
    status = models.CharField(
        choices=STATUS,
        verbose_name=_("Applicant|Status"),
        blank=True,
        null=True,
        max_length=20,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Account"),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    # Personal
    first_name = models.CharField(_("First name"), max_length=255)
    last_name = models.CharField(_("Surname"), max_length=255)
    patronymic = models.CharField(
        _("Patronymic"), max_length=255, blank=True, null=True
    )
    email = models.EmailField(_("Email"), help_text=_("Applicant|email"))
    telegram_username = models.CharField(
        _("Telegram"), max_length=255, blank=True, null=True
    )
    is_unsubscribed = models.BooleanField(
        _("Unsubscribed"),
        default=False,
        db_index=True,
        help_text=_("Unsubscribe from future notifications"),
    )
    phone = models.CharField(
        _("Contact phone"), max_length=42, help_text=_("Applicant|phone")
    )
    residence_city = models.ForeignKey(to="admission.ResidenceCity", verbose_name=_("Residence city"),
                                       blank=True, null=True, on_delete=models.SET_NULL)
    # Since the 2023 campaign, we have been using it as storage for cities not listed in ResidenceCity.
    living_place = models.CharField(
        _("Living Place"), max_length=255, null=True, blank=True
    )
    birth_date = models.DateField(_("Date of Birth"), blank=True, null=True)
    # Social Networks
    stepic_id = models.CharField(
        _("Stepik ID"),
        help_text=_("Applicant|stepic_id"),
        max_length=255,
        blank=True,
        null=True,
    )
    yandex_login = models.CharField(
        _("Yandex Login"),
        max_length=80,
        help_text=_("Applicant|yandex_login"),
        null=True,
        blank=True,
    )
    yandex_login_q = models.CharField(
        _("Yandex Login (normalized)"),
        max_length=80,
        help_text=_("Applicant|yandex_id_normalization"),
        editable=False,
        null=True,
        blank=True,
    )
    github_login = models.CharField(
        _("Github Login"),
        max_length=255,
        help_text=_("Applicant|github_login"),
        null=True,
        blank=True,
    )
    # Education
    partner = models.ForeignKey("users.PartnerTag", verbose_name=_("Partner"),
                                null=True, blank=True, on_delete=models.SET_NULL)
    is_studying = models.BooleanField(_("Are you studying?"), null=True)
    university = models.ForeignKey(
        "universities.University",
        verbose_name=_("Universities|University"),
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    university_legacy = models.ForeignKey(
        "core.University",
        verbose_name=_("Applicant|University"),
        on_delete=models.PROTECT,
        related_name="+",
        blank=True,
        null=True,
    )
    university_other = models.CharField(
        _("University (Other)"), max_length=255, null=True, blank=True
    )
    faculty = models.TextField(
        _("Faculty"), help_text=_("Applicant|faculty"), blank=True, null=True
    )
    level_of_education = models.CharField(
        _("Course"),
        choices=AcademicDegreeLevels.choices,
        help_text=_("Applicant|course"),
        max_length=12,
        blank=True,
        null=True,
    )
    year_of_graduation = models.PositiveSmallIntegerField(
        verbose_name=_("Graduation Year"), blank=True, null=True
    )
    graduate_work = models.TextField(
        _("Graduate work"),
        help_text=_("Applicant|graduate_work_or_dissertation"),
        null=True,
        blank=True,
    )
    online_education_experience = models.TextField(
        _("Online Education Exp"),
        help_text=_("Applicant|online_education_experience"),
        null=True,
        blank=True,
    )
    # Work related questions
    experience = models.TextField(
        _("Experience"),
        help_text=_("Applicant|work_or_study_experience"),
        null=True,
        blank=True,
    )
    has_internship = models.BooleanField(
        _("Have you had an internship?"), help_text=_("Applicant|Has internship"), null=True
    )
    internship_workplace = models.CharField(
        _("Internship workplace"),
        help_text=_("Applicant|Internship workplace"),
        max_length=255,
        null=True,
        blank=True,
    )
    internship_position = models.CharField(
        _("Internship position"),
        help_text=_("Applicant|Internship position"),
        max_length=255,
        null=True,
        blank=True,
    )
    has_job = models.BooleanField(
        _("Do you work?"), help_text=_("Applicant|has_job"), null=True
    )
    workplace = models.CharField(
        _("Workplace"),
        help_text=_("Applicant|workplace"),
        max_length=255,
        null=True,
        blank=True,
    )
    position = models.CharField(
        _("Position"),
        help_text=_("Applicant|position"),
        max_length=255,
        null=True,
        blank=True,
    )

    motivation = models.TextField(
        _("Your motivation"),
        help_text=_("Applicant|motivation_why"),
        blank=True,
        null=True,
    )
    probability = models.TextField(
        _("Probability"), help_text=_("Applicant|probability"), null=True, blank=True
    )
    preferred_study_programs = MultiSelectField(
        _("Study program"),
        help_text=_("Applicant|study_program"),
        choices=STUDY_PROGRAMS,
        max_length=255,
        blank=True,
    )
    # TODO: Store all study program notes in this field in label + value format instead
    #  of separated preferred_study_programs_*_note fields
    preferred_study_program_notes = models.TextField(
        _("Study Program Notes"), null=True, blank=True
    )
    preferred_study_programs_dm_note = models.TextField(
        _("Study program (DM note)"),
        help_text=_("Applicant|study_program_dm"),
        null=True,
        blank=True,
    )
    preferred_study_programs_se_note = models.TextField(
        _("Study program (SE note)"),
        help_text=_("Applicant|study_program_se"),
        null=True,
        blank=True,
    )
    preferred_study_programs_cs_note = models.TextField(
        _("Study program (CS note)"),
        help_text=_("Applicant|study_program_cs"),
        null=True,
        blank=True,
    )
    # Note: replace with m2m relation first if you need some statistics
    # based on field below
    where_did_you_learn = MultiSelectField(
        _("Where did you learn about admission?"), choices=INFO_SOURCES, blank=True
    )
    where_did_you_learn_other = models.CharField(
        _("Where did you learn about admission? (other)"),
        max_length=255,
        null=True,
        blank=True,
    )
    your_future_plans = models.TextField(
        _("Future plans"), help_text=_("Applicant|future_plans"), blank=True, null=True
    )
    additional_info = models.TextField(
        _("Additional Info"),
        help_text=_("Applicant|additional_info"),
        blank=True,
        null=True,
    )
    admin_note = models.TextField(
        _("Admin note"), help_text=_("Applicant|admin_note"), blank=True, null=True
    )
    # Key-value store for fields specific to admission campaigns
    data = models.JSONField(_("Data"), blank=True, null=True)
    # Any useful data like application form integration log
    # FIXME: merge into data json field, then remove
    meta = models.JSONField(blank=True, null=True, editable=False)

    class Meta:
        app_label = "admission"
        verbose_name = _("Applicant")
        verbose_name_plural = _("Applicants")
        unique_together = [("email", "campaign")]

    objects = models.Manager()
    subscribed = ApplicantSubscribedManager()

    @transaction.atomic
    def save(self, **kwargs):
        created = self.pk is None
        if self.yandex_login:
            self.yandex_login_q = normalize_yandex_login(self.yandex_login)
        super().save(**kwargs)
        if created:
            self._assign_testing()
        if self.is_unsubscribed:
            # Looking for other applicants with the same email and
            # unsubscribe them too.
            (
                Applicant.objects.filter(email=self.email)
                .exclude(pk=self.pk)
                .update(is_unsubscribed=True)
            )

    def _assign_testing(self):
        testing = Test(applicant=self, status=ChallengeStatuses.NEW)
        testing.save()

    def created_local(self, tz=None):
        if not tz:
            tz = self.get_timezone()
        return timezone.localtime(self.created, timezone=tz)

    @property
    def full_name(self):
        parts = [self.last_name, self.first_name, self.patronymic]
        return smart_str(" ".join(part for part in parts if part).strip())

    def clean(self):
        if self.yandex_login:
            self.yandex_login_q = self.yandex_login.lower().replace("-", ".")

    def get_living_place_display(self):
        if not self.living_place and self.campaign.branch.city_id:
            return self.campaign.branch.name
        return self.living_place

    @property
    def is_alternative_track(self) -> bool:
        if not isinstance(self.data, dict):
            return False
        return self.data.get("new_track") is True

    @property
    def alternative_track_info(self) -> dict:
        if not isinstance(self.data, dict):
            return {}
        return {
            "Есть ли у вас научные статьи": self.data.get("new_track_scientific_articles"),
            "Есть ли у вас открытые проекты вашего авторства": self.data.get("new_track_projects"),
            "Есть ли у вас посты или статьи о технологиях": self.data.get("new_track_tech_articles"),
            "Расскажите более подробно о каком-нибудь из своих проектов": self.data.get("new_track_project_details"),
        }

    @property
    def has_ticket(self) -> bool:
        if not isinstance(self.data, dict):
            return False
        return self.data.get("ticket_access")

    @cached_property
    def is_yds_applicant(self):
        return self.campaign.branch.site.id == YDS_SITE_ID

    @classmethod
    def get_name_by_status_code(cls, code):
        for status_code, status_name in cls.STATUS:
            if status_code == code:
                return status_name
        return ""

    def get_absolute_url(self):
        return reverse("admission:applicants:detail", args=[self.pk])

    def __str__(self):
        if self.campaign_id:
            return smart_str("{} [{}]".format(self.full_name, self.campaign))
        else:
            return smart_str(self.full_name)

    def get_testing_record(self) -> Optional["Test"]:
        try:
            return self.online_test
        except Test.DoesNotExist:
            return None

    def get_exam_record(self) -> Optional["Exam"]:
        try:
            return self.exam
        except Exam.DoesNotExist:
            return None

    def get_university_display(self) -> Optional[str]:
        if self.university is not None:
            return self.university.name
        elif self.university_other:
            return self.university_other
        elif self.university_legacy:
            return self.university_legacy.abbr or self.university_legacy.name
        return None

    # FIXME: filter by site
    def get_similar(self):
        conditions = [
            Q(email=self.email),
            (
                Q(first_name__iexact=self.first_name)
                & Q(last_name__iexact=self.last_name)
                & Q(patronymic__iexact=self.patronymic)
            ),
        ]
        if self.phone:
            conditions.append(Q(phone=self.phone))
        if self.stepic_id:
            conditions.append(Q(stepic_id=self.stepic_id))
        if self.yandex_login_q:
            conditions.append(Q(yandex_login_q=self.yandex_login_q))
        q = conditions.pop()
        for c in conditions:
            q |= c
        return Applicant.objects.filter(~Q(id=self.pk) & q)


def contest_assignments_upload_to(instance, filename):
    # TODO: Can be visible for unauthenticated. Is it ok?
    return instance.FILE_PATH_TEMPLATE.format(
        contest_id=instance.contest_id, filename=filename
    )


def validate_json_container(value):
    """
    Doesn't call if value is empty. This behavior checked in model clean method
    """
    if not isinstance(value, dict):
        raise ValidationError("Serialized JSON should have dict as a container.")


# TODO: add Contest provider (yandex/stepic), then change YandexContestIntegration.yandex_contest_id to FK
class Contest(models.Model):
    FILE_PATH_TEMPLATE = "contest/{contest_id}/assignments/{filename}"
    TYPE_TEST = ContestTypes.TEST
    TYPE_EXAM = ContestTypes.EXAM
    # TODO: replace with ContestTypes
    TYPES = ContestTypes.choices
    campaign = models.ForeignKey(
        Campaign,
        verbose_name=_("Contest|Campaign"),
        on_delete=models.PROTECT,
        related_name="contests",
    )
    type = models.IntegerField(_("Type"), choices=ContestTypes.choices)
    contest_id = models.CharField(
        _("Contest #ID"),
        help_text=_("Applicant|yandex_contest_id"),
        max_length=42,
        blank=True,
        null=True,
    )
    details = models.JSONField(
        verbose_name=_("Details"),
        blank=True,
        default=dict,
    )
    file = ConfigurableStorageFileField(
        _("Assignments in pdf format"),
        blank=True,
        upload_to=contest_assignments_upload_to,
        max_length=200,
        storage=private_storage,
    )

    class Meta:
        app_label = "admission"
        verbose_name = _("Contest")
        verbose_name_plural = _("Contests")

    def file_url(self):
        return self.file.url

    def __str__(self):
        return self.contest_id


class YandexContestImportResults(NamedTuple):
    on_scoreboard: int
    updated: int


class YandexContestIntegration(models.Model):
    CONTEST_TYPE: ClassVar[int]
    applicant: Any

    yandex_contest_id = models.CharField(
        _("Contest #ID"),
        help_text=_("Applicant|yandex_contest_id"),
        max_length=42,
        blank=True,
        null=True,
    )
    contest_participant_id = models.IntegerField(
        _("Participant ID"),
        help_text=_("participant_id in Yandex.Contest"),
        null=True,
        blank=True,
    )
    contest_status_code = models.IntegerField(
        "Yandex API Response", null=True, blank=True
    )
    status = models.CharField(
        choices=ChallengeStatuses.choices,
        default=ChallengeStatuses.NEW,
        verbose_name=_("Status"),
        help_text=_(
            "Choose `manual score input` to avoid synchronization with "
            "contest results"
        ),
        max_length=15,
    )

    class Meta:
        app_label = "admission"
        abstract = True

    @classmethod
    def check(cls, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(cls._check_applicant_fk())
        errors.extend(cls._check_type_attr())
        return errors

    @classmethod
    def _check_type_attr(cls):
        errors = []
        if not hasattr(cls, "CONTEST_TYPE"):
            errors.append(
                checks.Error(
                    f"`{cls} is a subclass of YandexContestIntegration but no "
                    f"contest type information was provided",
                    hint=f"define {cls.__name__}.CONTEST_TYPE attribute value",
                    obj=cls,
                    id="admission.E003",
                )
            )
        else:
            types = (k for k, v in Contest._meta.get_field("type").choices)
            if cls.CONTEST_TYPE not in types:
                errors.append(
                    checks.Error(
                        f"`{cls.__name__}.CONTEST_TYPE value must be defined "
                        f"in Contest.type field choices",
                        obj=cls,
                        id="admission.E004",
                    )
                )
        return errors

    @classmethod
    def _check_applicant_fk(cls):
        errors = []
        try:
            applicant = cls._meta.get_field("applicant")
            if not applicant.is_relation or not issubclass(
                applicant.remote_field.model, Applicant
            ):
                errors.append(
                    checks.Error(
                        f"`{cls}.applicant` is not a FK to Applicant model",
                        hint="define applicant = OneToOneField(Applicant, ...)",
                        obj=cls,
                        id="admission.E002",
                    )
                )
        except FieldDoesNotExist:
            errors.append(
                checks.Error(
                    f"`{cls.__name__}` is a subclass of YandexContestIntegration"
                    f" and must define `applicant` field",
                    hint="define applicant = OneToOneField(Applicant, ...)",
                    obj=cls,
                    id="admission.E001",
                )
            )
        return errors

    def register_in_contest(self, api):
        """
        Registers participant in the contest and saves response
        info (status_code, participant_id)
        """
        applicant = self.applicant
        try:
            status_code, data = api.register_in_contest(
                applicant.yandex_login, self.yandex_contest_id
            )
        except YandexContestError:
            raise
        update_fields = {
            "status": ChallengeStatuses.REGISTERED,
            "contest_status_code": status_code,
        }
        if status_code in (RegisterStatus.CREATED, RegisterStatus.OK):
            participant_id = data
            update_fields["contest_participant_id"] = participant_id
        else:  # 409 - already registered for this contest
            registered = (
                self.__class__.objects.filter(
                    yandex_contest_id=self.yandex_contest_id,
                    contest_status_code=RegisterStatus.CREATED,
                    applicant__campaign_id=applicant.campaign_id,
                    applicant__yandex_login=applicant.yandex_login,
                )
                .exclude(contest_participant_id__isnull=True)
                .only("contest_participant_id")
                .first()
            )
            # 1. Admins/judges could be registered directly through contest
            # admin, so we haven't info about there participant id and
            # can't easily get there results later, but still allow them
            # testing application form
            # 2. When registering user in contest on `read timeout` response
            # we lost information about there participant id without any
            # ability to restore it through API (until the participant
            # appears in results table)
            if registered:
                participant_id = registered.contest_participant_id
                update_fields["contest_participant_id"] = participant_id
        updated = self.__class__.objects.filter(applicant=applicant).update(
            **update_fields
        )
        if updated:
            for k, v in update_fields.items():
                setattr(self, k, v)

    @classmethod
    def import_scores(cls, *, api, contest: Contest) -> YandexContestImportResults:
        """
        Imports contest results page by page.

        Since scoreboard can be modified at any moment we could miss some
        results during the importing if someone has improved his position
        and moved to a scoreboard `page` that has already been processed.
        """
        paging = {"page_size": 50, "page": 1}
        scoreboard_total = 0
        updated_total = 0
        if not contest.details:
            contest.details = {}
        while True:
            try:
                status, json_data = api.standings(contest.contest_id, **paging)
                # XXX: Assignments order on a scoreboard could differ from
                # the similar contest problems API call response
                contest.details["titles"] = [t["name"] for t in json_data["titles"]]
                contest.save(update_fields=("details",))
                page_total = 0
                for row in json_data["rows"]:
                    scoreboard_total += 1
                    page_total += 1
                    total_score_str: str = row["score"].replace(",", ".")
                    total_score = int(round(float(total_score_str)))
                    score_details = [a["score"] for a in row["problemResults"]]
                    update_fields = {
                        "score": total_score,
                        "details": {"scores": score_details},
                    }
                    yandex_login = row["participantInfo"]["login"]
                    participant_id = row["participantInfo"]["id"]
                    updated = cls.objects.filter(
                        Q(applicant__yandex_login=yandex_login)
                        | Q(contest_participant_id=participant_id),
                        applicant__campaign_id=contest.campaign_id,
                        yandex_contest_id=contest.contest_id,
                        status=ChallengeStatuses.REGISTERED,
                    ).update(**update_fields)
                    updated_total += updated
                if page_total < paging["page_size"]:
                    break
                paging["page"] += 1
            except YandexContestError as e:
                raise
        return YandexContestImportResults(
            on_scoreboard=scoreboard_total, updated=updated_total
        )


class ApplicantRandomizeContestMixin:
    pk: Optional[int]
    applicant: Any

    def compute_contest_id(self, contest_type, group_size=1) -> Optional[int]:
        """Selects contest id in a round-robin manner."""
        campaign_id = self.applicant.campaign_id
        contests = list(
            Contest.objects.filter(campaign_id=campaign_id, type=contest_type)
            .values_list("contest_id", flat=True)
            .order_by("contest_id")
        )
        if not contests:
            return None
        if contest_type == Contest.TYPE_EXAM:
            manager = Exam.objects
        elif contest_type == Contest.TYPE_TEST:
            manager = Test.objects
        else:
            raise ValueError("Unknown contest type")
        qs = manager.filter(applicant__campaign_id=campaign_id)
        if self.pk is None:
            serial_number = qs.count() + 1
        else:
            # Assume records are ordered by PK
            serial_number = qs.filter(pk__lte=self.pk).count()
        return get_next_process(serial_number, contests, group_size)


class Test(TimeStampedModel, YandexContestIntegration, ApplicantRandomizeContestMixin):
    CONTEST_TYPE = Contest.TYPE_TEST

    applicant = models.OneToOneField(
        Applicant,
        verbose_name=_("Applicant"),
        on_delete=models.PROTECT,
        related_name="online_test",
    )
    score = models.PositiveSmallIntegerField(
        verbose_name=_("Score"), null=True, blank=True
    )
    details = models.JSONField(
        verbose_name=_("Details"),
        blank=True,
        default=dict,
    )

    class Meta:
        app_label = "admission"
        verbose_name = _("Testing Result")
        verbose_name_plural = _("Testing Results")

    def __str__(self):
        """Import/export get repr before instance created in db."""
        if self.applicant_id:
            return self.applicant.full_name
        else:
            return smart_str(self.score)

    def score_display(self):
        return self.score if self.score is not None else "-"

    def save(self, **kwargs):
        created = self.pk is None
        if (
            created
            and self.status == ChallengeStatuses.NEW
            and not self.yandex_contest_id
        ):
            contest_id = self.compute_contest_id(Contest.TYPE_TEST)
            if contest_id:
                self.yandex_contest_id = contest_id
        super().save(**kwargs)


class Exam(TimeStampedModel, YandexContestIntegration, ApplicantRandomizeContestMixin):
    CONTEST_TYPE = Contest.TYPE_EXAM

    applicant = models.OneToOneField(
        Applicant,
        verbose_name=_("Applicant"),
        on_delete=models.PROTECT,
        related_name="exam",
    )
    score = ScoreField(
        verbose_name=_("Score"),
        decimal_places=3,
        # Avoid loading empty values with admin interface
        null=True,
        blank=True,
    )
    details = models.JSONField(verbose_name=_("Details"), blank=True, null=True)

    class Meta:
        app_label = "admission"
        verbose_name = _("Exam")
        verbose_name_plural = _("Exams")

    def save(self, **kwargs):
        created = self.pk is None
        if (
            created
            and self.status == ChallengeStatuses.NEW
            and not self.yandex_contest_id
        ):
            contest_id = self.compute_contest_id(Contest.TYPE_EXAM)
            if contest_id:
                self.yandex_contest_id = contest_id
        super().save(**kwargs)

    def __str__(self):
        """Import/export get repr before instance created in db."""
        if self.applicant_id:
            return self.applicant.full_name
        else:
            return smart_str(self.score)

    def score_display(self):
        return self.score if self.score is not None else "-"


class InterviewAssignment(models.Model):
    campaign = models.ForeignKey(
        Campaign,
        verbose_name=_("InterviewAssignments|Campaign"),
        on_delete=models.PROTECT,
        related_name="interview_assignments",
    )
    name = models.CharField(_("InterviewAssignments|name"), max_length=255)
    description = models.TextField(
        _("Assignment description"), help_text=_("TeX support")
    )
    solution = models.TextField(
        _("Assignment solution"), help_text=_("TeX support"), null=True, blank=True
    )

    class Meta:
        app_label = "admission"
        verbose_name = _("Interview assignment")
        verbose_name_plural = _("Interview assignments")

    def __str__(self):
        return smart_str(self.name)


class InterviewFormat(models.Model):
    campaign = models.ForeignKey(
        Campaign,
        verbose_name=_("Campaign"),
        on_delete=models.CASCADE,
        related_name="interview_formats",
    )
    format = models.CharField(
        verbose_name=_("Format Name"), choices=InterviewFormats.choices, max_length=255
    )
    confirmation_template = models.ForeignKey(
        EmailTemplate,
        verbose_name=_("Confirmation Template"),
        related_name="+",
        help_text=_(
            "Template for confirmation email that the interview was "
            "scheduled. Leave blank if there is no need to send "
            "confirmation email"
        ),
        blank=True,
        null=True,
        on_delete=models.PROTECT,
    )
    reminder_template = models.ForeignKey(
        EmailTemplate,
        verbose_name=_("Reminder Template"),
        related_name="+",
        help_text=_(
            "Template for interview reminder email. Notification will "
            "be generated only on interview creation through slots "
            "mechanism."
        ),
        on_delete=models.PROTECT,
    )
    remind_before_start = models.DurationField(
        verbose_name=_("Remind Before Start"),
        help_text=_(
            "Helps to calculate schedule time of the reminder. "
            "Specify timedelta that will be subtracted from the "
            "interview start time."
        ),
        default="23:59:59",
    )

    class Meta:
        app_label = "admission"
        verbose_name = _("Interview Format")
        verbose_name_plural = _("Interview Formats")
        constraints = [
            models.UniqueConstraint(
                fields=("campaign", "format"), name="unique_format_per_campaign"
            ),
        ]

    def __str__(self):
        return self.format


class Interview(TimezoneAwareMixin, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = "venue"

    APPROVAL = "approval"
    APPROVED = "waiting"
    DEFERRED = "deferred"
    CANCELED = "canceled"
    COMPLETED = "completed"
    STATUSES = (
        (APPROVAL, _("Approval")),
        (DEFERRED, _("Deferred")),
        (CANCELED, _("Canceled")),
        (APPROVED, _("Approved")),
        (COMPLETED, _("Completed")),
    )
    TRANSITION_STATUSES = [DEFERRED, CANCELED, APPROVAL]

    applicant = models.ForeignKey(
        Applicant,
        verbose_name=_("Applicant"),
        on_delete=models.PROTECT,
        related_name="interviews",
    )
    section = models.CharField(
        choices=InterviewSections.choices,
        verbose_name=_("Interview|Section"),
        max_length=15,
    )
    date = TimezoneAwareDateTimeField(_("When"))
    status = models.CharField(
        choices=STATUSES,
        default=APPROVAL,
        verbose_name=_("Interview|Status"),
        max_length=15,
    )
    venue = models.ForeignKey(
        Location,
        verbose_name=_("Venue"),
        on_delete=models.PROTECT,
        related_name="+",
        blank=False,
        null=True,
    )
    interviewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Interview|Interviewers"),
        limit_choices_to={"group__role": Roles.INTERVIEWER},
    )
    assignments = models.ManyToManyField(
        "InterviewAssignment", verbose_name=_("Interview|Assignments"), blank=True
    )
    secret_code = models.UUIDField(
        verbose_name=_("Secret code"), editable=False, default=uuid.uuid4
    )
    note = models.TextField(_("Note"), blank=True, null=True)

    class Meta:
        app_label = "admission"
        verbose_name = _("Interview")
        verbose_name_plural = _("Interviews")
        constraints = [
            models.UniqueConstraint(
                fields=("applicant", "section"),
                name="unique_interview_section_per_applicant",
            ),
        ]

    def __str__(self):
        return smart_str(self.applicant)

    def save(self, **kwargs):
        created = self.pk is None
        self.full_clean()
        super().save(**kwargs)

    def date_local(self, tz=None):
        if not tz:
            tz = self.get_timezone()
        return timezone.localtime(self.date, timezone=tz)

    def clean(self):
        if self.status != self.APPROVAL and not self.date:
            raise ValidationError("You can't change status without date set up")

    def get_absolute_url(self):
        return reverse("admission:interviews:detail", args=[self.pk])

    def get_public_assignments_url(self):
        return reverse(
            "appointment:interview_assignments",
            kwargs={
                "year": self.applicant.campaign.year,
                "secret_code": str(self.secret_code).replace("-", ""),
            },
        )

    def in_transition_state(self):
        return self.status in self.TRANSITION_STATUSES

    @property
    def average_score(self) -> Optional[Union[float, Decimal]]:
        # `_average_score` can be calculated with query annotation to improve
        # performance
        if hasattr(self, "_average_score"):
            return self._average_score  # type: ignore[has-type]
        scores = [comment.score for comment in self.comments.all()]
        if scores:
            self._average_score = float(sum(scores)) / len(scores)
            return self._average_score
        return None

    def get_average_score_display(self, decimal_pos=2):
        if self.average_score is None:
            return "N/A"
        return numberformat.format(self.average_score, ".", decimal_pos)

    @property
    def rating_system(self) -> Type[DjangoChoices]:
        # TODO: consider to move rating systems to DB
        if self.applicant.campaign.branch.site.name == "Yandex School of Data Analysis":
            return YandexDataSchoolInterviewRatingSystem
        return DefaultInterviewRatingSystem


class Comment(TimeStampedModel):
    interview = models.ForeignKey(
        Interview,
        verbose_name=_("Interview"),
        on_delete=models.PROTECT,
        related_name="comments",
    )
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Interviewer"),
        on_delete=models.PROTECT,
        related_name="interview_comments",
    )
    text = models.TextField(_("Text"), blank=True, null=True)
    score = models.SmallIntegerField(verbose_name=_("Score"))

    class Meta:
        app_label = "admission"
        verbose_name = _("Comment")
        verbose_name_plural = _("Comments")
        unique_together = ("interview", "interviewer")

    def __str__(self):
        return smart_str(
            "{} [{}]".format(
                self.interviewer.get_full_name(), self.interview.applicant.full_name
            )
        )


class InterviewStream(TimezoneAwareMixin, DerivableFieldsMixin, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = "venue"
    formats = InterviewFormats  # TODO: remove

    campaign = models.ForeignKey(
        Campaign,
        verbose_name=_("Campaign"),
        on_delete=models.CASCADE,
        related_name="interview_streams",
    )
    section = models.CharField(
        choices=InterviewSections.choices,
        verbose_name=_("Interview|Section"),
        max_length=15,
    )
    format = models.CharField(
        verbose_name=_("Interview Format"),
        choices=InterviewFormats.choices,
        max_length=42,
    )
    interview_format = models.ForeignKey(
        InterviewFormat,
        verbose_name=_("Interview Format"),
        on_delete=models.CASCADE,
        editable=False,
        related_name="+",
    )
    date = models.DateField(_("Interview day"))
    start_at = models.TimeField(_("Period start"))
    end_at = models.TimeField(_("Period end"))
    duration = models.IntegerField(
        _("Slot duration"), validators=[MinValueValidator(10)], default=30
    )
    # TODO: do not change if some slots already was taken
    venue = models.ForeignKey(
        Location,
        verbose_name=_("Interview venue"),
        on_delete=models.PROTECT,
        related_name="streams",
    )
    with_assignments = models.BooleanField(
        _("Has assignments"),
        help_text=_(
            "Based on this flag, student should arrive 30 min " "before or not"
        ),
    )
    interviewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Interview|Interviewers"),
        limit_choices_to={"group__role": Roles.INTERVIEWER},
    )
    slots_count = models.PositiveIntegerField(editable=False, default=0)
    slots_occupied_count = models.PositiveIntegerField(editable=False, default=0)

    derivable_fields = ["slots_count", "slots_occupied_count"]

    class Meta:
        app_label = "admission"
        verbose_name = _("Interview stream")
        verbose_name_plural = _("Interview streams")

    def save(self, **kwargs):
        created = self.pk is None
        self.interview_format = InterviewFormat.objects.get(
            campaign=self.campaign, format=self.format
        )
        super().save(**kwargs)
        if created:
            # Generate slots
            step = datetime.timedelta(minutes=self.duration)
            slots = [
                InterviewSlot(start_at=start_at, end_at=end_at, stream=self)
                for start_at, end_at in slot_range(self.start_at, self.end_at, step)
            ]
            InterviewSlot.objects.bulk_create(slots)
            # It's possible to avoid query below by separating slots bulk
            # creation and objects initialization, but let's store them in
            # one place
            self.slots_count = len(slots)
            (
                InterviewStream.objects.filter(pk=self.pk).update(
                    slots_count=self.slots_count
                )
            )

    def __str__(self):
        return "{}, {}-{}".format(
            date_format(self.date, settings.DATE_FORMAT),
            time_format(self.start_at),
            time_format(self.end_at),
        )

    def clean(self):
        if self.format and self.campaign:
            if not InterviewFormat.objects.filter(
                format=self.format, campaign=self.campaign
            ).exists():
                error_msg = _(
                    "Interview format settings are not found. "
                    "Create settings <a href='{}'>here</a>."
                )
                add_url = reverse("admin:admission_interviewformat_add")
                msg = mark_safe(error_msg.format(add_url))
                raise ValidationError(msg)
        if self.start_at and self.end_at and self.duration:
            self.start_at = self.start_at.replace(second=0, microsecond=0)
            self.end_at = self.end_at.replace(second=0, microsecond=0)
            start_at = datetime.timedelta(
                hours=self.start_at.hour, minutes=self.start_at.minute
            )
            end_at = datetime.timedelta(
                hours=self.end_at.hour, minutes=self.end_at.minute
            )
            diff = (end_at - start_at).total_seconds() / 60
            if diff < self.duration:
                raise ValidationError(
                    _("Stream duration can't be less than slot duration")
                )

    def _compute_slots_count(self):
        total = Subquery(
            InterviewSlot.objects.filter(stream_id=OuterRef("id"))
            .values("stream")
            .annotate(total=Count("*"))
            .values("total")
        )
        (
            InterviewStream.objects.filter(pk=self.pk).update(
                slots_count=Coalesce(total, Value(0))
            )
        )
        # Avoid triggering .save()
        return False

    def _compute_slots_occupied_count(self):
        total = Subquery(
            InterviewSlot.objects.filter(
                stream_id=OuterRef("id"), interview__isnull=False
            )
            .values("stream")
            .annotate(total=Count("*"))
            .values("total")
        )
        (
            InterviewStream.objects.filter(pk=self.pk).update(
                slots_occupied_count=Coalesce(total, Value(0))
            )
        )
        # Avoid triggering .save()
        return False

    @property
    def slots_free_count(self):
        return self.slots_count - self.slots_occupied_count


class InterviewSlotQuerySet(query.QuerySet):
    def lock(self, slot, interview):
        """Try to fill interview slot in a CAS manner"""
        return self.filter(pk=slot.pk, interview_id__isnull=True).update(
            interview_id=interview.pk
        )


class InterviewSlot(TimeStampedModel):
    interview = models.OneToOneField(
        Interview,
        verbose_name=_("Interview"),
        on_delete=models.SET_NULL,
        related_name="slot",
        null=True,
        blank=True,
    )
    start_at = models.TimeField(_("Interview start"))
    end_at = models.TimeField(_("Interview end"))
    stream = models.ForeignKey(
        InterviewStream,
        verbose_name=_("Interview stream"),
        on_delete=models.PROTECT,
        related_name="slots",
    )

    class Meta:
        app_label = "admission"
        ordering = ["start_at"]
        verbose_name = _("Interview slot")
        verbose_name_plural = _("Interview slots")

    objects = InterviewSlotQuerySet.as_manager()

    def __str__(self):
        return time_format(self.start_at)

    @property
    def is_empty(self):
        return not bool(self.interview_id)

    @property
    def datetime_local(self):
        date = datetime.datetime.combine(self.stream.date, self.start_at)
        return timezone.make_aware(date, self.stream.get_timezone())


class InterviewInvitationQuerySet(query.QuerySet):
    # FIXME: move to selectors
    def for_applicant(self, applicant):
        """Returns last active invitation for requested user"""
        today = timezone.now()
        return (
            self.filter(Q(expired_at__gt=today) | Q(expired_at__isnull=True))
            .filter(applicant=applicant)
            .order_by("-pk")
            .first()
        )


class InterviewInvitation(TimeStampedModel):
    applicant = models.ForeignKey(
        Applicant,
        verbose_name=_("Applicant"),
        on_delete=models.PROTECT,
        related_name="interview_invitations",
    )
    status = models.CharField(
        choices=InterviewInvitationStatuses.choices,
        default=InterviewInvitationStatuses.NO_RESPONSE,
        verbose_name=_("Status"),
        max_length=10,
    )
    streams = models.ManyToManyField(
        InterviewStream,
        verbose_name=_("Interview streams"),
        related_name="interview_invitations",
    )
    secret_code = models.UUIDField(
        verbose_name=_("Secret code"), default=uuid.uuid4, unique=True
    )
    expired_at = models.DateTimeField(_("Expired at"))
    interview = models.ForeignKey(
        Interview,
        verbose_name=_("Interview"),
        on_delete=models.CASCADE,
        related_name="invitations",
        null=True,
        blank=True,
    )

    objects = InterviewInvitationQuerySet.as_manager()

    class Meta:
        app_label = "admission"
        verbose_name = _("Interview invitation")
        verbose_name_plural = _("Interview invitations")

    def save(self, **kwargs):
        created = self.pk is None
        super().save(**kwargs)
        if created and not self.interview_id:
            # Update status if we send invitation before
            # summing up the exam results
            if self.applicant.status == Applicant.PERMIT_TO_EXAM:
                (
                    Applicant.objects.filter(pk=self.applicant_id).update(
                        status=Applicant.INTERVIEW_TOBE_SCHEDULED
                    )
                )

    def __str__(self):
        return str(self.applicant)

    @property
    def is_expired(self):
        return (
            self.status == InterviewInvitationStatuses.EXPIRED
            or timezone.now() >= self.expired_at
        )

    @property
    def is_accepted(self):
        return bool(self.interview_id)

    @property
    def is_declined(self):
        return self.status == InterviewInvitationStatuses.DECLINED

    def get_absolute_url(self):
        return reverse(
            "appointment:select_time_slot",
            kwargs={
                "year": self.applicant.campaign.year,
                "secret_code": str(self.secret_code).replace("-", ""),
            },
        )

    def get_status_display(self):
        status = self.status
        if self.status == InterviewInvitationStatuses.NO_RESPONSE and self.is_expired:
            status = InterviewInvitationStatuses.EXPIRED
        return InterviewInvitationStatuses.values[status]


class Acceptance(TimestampedModel):
    WAITING = "new"
    CONFIRMED = "confirmed"
    CONFIRMATION_CODE_LENGTH = 16

    status = models.CharField(
        verbose_name=_("Status"),
        max_length=12,
        choices=[
            (WAITING, _("Waiting for Confirmation")),
            (CONFIRMED, _("Confirmed")),
        ],
        default=WAITING,
    )
    applicant = models.OneToOneField(
        Applicant,
        verbose_name=_("Applicant"),
        on_delete=models.PROTECT,
        related_name="+",
    )
    access_key = models.CharField(
        max_length=DIGEST_MAX_LENGTH, editable=False, db_index=True
    )
    confirmation_code = models.CharField(
        verbose_name=_("Authorization Code"), max_length=24, editable=False
    )

    class Meta:
        app_label = "admission"
        verbose_name = _("Acceptance for Studies")
        verbose_name_plural = _("Acceptances for Studies")

    def __str__(self):
        return f"{self.applicant.full_name}"

    def save(self, **kwargs):
        created = self.pk is None
        if created:
            self.access_key = generate_hash(
                b"acceptance", force_bytes(self.applicant.email)
            )
            self.confirmation_code = generate_random_string(
                self.CONFIRMATION_CODE_LENGTH, alphabet=string.hexdigits
            )
        super().save(**kwargs)

    def get_absolute_url(self):
        return reverse(
            "admission:acceptance:confirmation_form",
            kwargs={
                "year": self.applicant.campaign.year,
                "access_key": self.access_key,
            },
        )

    @property
    def deadline_at(self) -> datetime.datetime:
        ends_at: Optional[
            datetime.datetime
        ] = self.applicant.campaign.confirmation_ends_at
        if not ends_at:
            return timezone.now() - datetime.timedelta(hours=2)
        return ends_at

    @property
    def is_expired(self):
        return timezone.now() >= self.deadline_at


class ResidenceCity(models.Model):
    external_id = models.PositiveIntegerField(
        _("External ID"), null=True, blank=True, editable=False
    )
    name = models.TextField(_("Name"))
    display_name = models.TextField(_("Display Name"))
    country = models.ForeignKey(
        "universities.Country",
        verbose_name=_("Country"),
        related_name="admission_cities",
        on_delete=models.PROTECT,
    )
    order = models.PositiveIntegerField(_("Order"), default=512)

    class Meta:
        app_label = "admission"
        verbose_name = _("Residence City")
        verbose_name_plural = _("Residence Cities")

    def __str__(self):
        return self.name


class CampaignCity(models.Model):
    campaign = models.ForeignKey(
        Campaign,
        verbose_name=_("Campaign"),
        related_name="+",
        on_delete=models.CASCADE,
    )

    city = models.ForeignKey(
        ResidenceCity,
        verbose_name=_("City"),
        related_name="+",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    class Meta:
        app_label = "admission"
        verbose_name = _("Campaign Available in City")
        verbose_name_plural = _("Campaigns Available in City")
        constraints = [
            models.UniqueConstraint(
                fields=["campaign", "city"], name="unique_campaign_per_city"
            ),
            models.UniqueConstraint(
                name="%(app_label)s_%(class)s_default_campaign_unique",
                fields=("campaign",),
                condition=Q(city__isnull=True),
            ),
        ]

    def __str__(self):
        return f"CampaignCity campaign={self.campaign} city={self.city}"
