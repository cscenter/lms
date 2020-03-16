# -*- coding: utf-8 -*-

import datetime
import uuid
from collections import OrderedDict
from typing import Optional, NamedTuple

from django.conf import settings
from django.core import checks
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, \
    MaxValueValidator
from django.db import models, transaction
from django.db.models import query, Q, FieldDoesNotExist
from django.utils import timezone, numberformat
from django.utils.encoding import smart_text
from django.utils.formats import date_format, time_format
from django.utils.translation import ugettext_lazy as _
from jsonfield import JSONField
from model_utils.models import TimeStampedModel
from multiselectfield import MultiSelectField
from post_office.models import Email, EmailTemplate, STATUS as EMAIL_STATUS
from post_office.utils import get_email_template

from admission.constants import ChallengeStatuses, INTERVIEW_FEEDBACK_TEMPLATE
from admission.utils import slot_range
from api.providers.yandex_contest import RegisterStatus, \
    Error as YandexContestError
from core.db.models import ScoreField
from core.models import Branch, Location
from core.timezone import TimezoneAwareModel
from core.urls import reverse
from learning.settings import AcademicDegreeLevels
from users.constants import Roles


def current_year():
    # Don't care about inaccuracy and use UTC timezone here
    return timezone.now().year


def validate_template_name(value):
    if not EmailTemplate.objects.filter(name=value).exists():
        raise ValidationError(
            _("Email template with name `%(template_name)s` doesn't exist"),
            params={'template_name': value},
        )


class Campaign(TimezoneAwareModel, models.Model):
    TIMEZONE_AWARE_FIELD_NAME = 'branch'

    year = models.PositiveSmallIntegerField(
        _("Campaign|Year"),
        validators=[MinValueValidator(2000)],
        default=current_year)
    branch = models.ForeignKey(Branch,
                               verbose_name=_("Branch"),
                               related_name="campaigns",
                               on_delete=models.PROTECT)
    online_test_max_score = models.SmallIntegerField(
        _("Campaign|Test_max_score"))
    online_test_passing_score = models.SmallIntegerField(
        _("Campaign|Test_passing_score"),
        help_text=_("Campaign|Test_passing_score-help"))
    exam_max_score = models.SmallIntegerField(
        _("Campaign|Exam_max_score"),
        null=True, blank=True)
    exam_passing_score = models.SmallIntegerField(
        _("Campaign|Exam_passing_score"),
        help_text=_("Campaign|Exam_passing_score-help"),
        null=True, blank=True)
    # FIXME: Make this field system/derivable or remove since now we store start and end
    current = models.BooleanField(
        _("Current campaign"),
        help_text=_("Show in application form list"),
        default=False)
    application_starts_at = models.DateTimeField(_("Application Starts on"))
    application_ends_at = models.DateTimeField(
        _("Application Ends on"),
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
    # FIXME: factory boy allows to save blank values for template names :<
    template_registration = models.CharField(
        _("Registration Template"),
        help_text=_("Template name for contest registration email"),
        validators=[validate_template_name],
        max_length=255)
    template_appointment = models.CharField(
        _("Invitation Template"),
        help_text=_("Template name for interview invitation email"),
        validators=[validate_template_name],
        max_length=255)
    template_interview_reminder = models.CharField(
        _("Interview Reminder Template"),
        help_text=_("Template name for interview reminder email"),
        validators=[validate_template_name],
        max_length=255)

    class Meta:
        verbose_name = _("Campaign")
        verbose_name_plural = _("Campaigns")

    def __str__(self):
        return smart_text(_("{}, {}").format(self.branch.name, self.year))

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
            contests = Contest.objects.filter(campaign_id=self.pk,
                                              type=Contest.TYPE_TEST).count()
            if not contests:
                msg = _("Before mark campaign as `current` - add contests "
                        "for testing")
                errors["__all__"] = msg
            if not self.access_token:
                errors["access_token"] = _("Empty access token")
        if errors:
            raise ValidationError(errors)

    @classmethod
    def get_active(cls):
        today = timezone.now()
        return (cls.objects
                .filter(current=True,
                        application_starts_at__lte=today,
                        application_ends_at__gt=today)
                .select_related('branch'))

    @property
    def is_active(self):
        today = timezone.now()
        return self.current and today <= self.application_ends_at


class University(models.Model):
    """
    Some universities are interesting for statistics. To avoid typos,
    different word order, abbreviations, letter case and
    many more things which could prevent accurately aggregate data, store
    target universities for each branch in this model.
    """
    name = models.CharField(_("University"),
                            max_length=255,
                            help_text=_("Perhaps also the faculty."))
    abbr = models.CharField(_("University abbreviation"), max_length=100,
                            blank=True, null=True)
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)
    branch = models.ForeignKey(Branch,
                               verbose_name=_("Branch"),
                               related_name="+",
                               null=True,
                               blank=True,
                               on_delete=models.PROTECT)

    class Meta:
        verbose_name = _("University")
        verbose_name_plural = _("Universities")

    def __str__(self):
        return smart_text(self.name)


class ApplicantQuerySet(models.QuerySet):
    pass


class _ApplicantSubscribedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_unsubscribed=False)


ApplicantSubscribedManager = _ApplicantSubscribedManager.from_queryset(
    ApplicantQuerySet)


class Applicant(TimezoneAwareModel, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = 'campaign'

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
    ACCEPT_PAID = 'accept_paid'
    WAITING_FOR_PAYMENT = 'waiting_for_payment'
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
        (ACCEPT_PAID, _('Accept on paid')),
        (WAITING_FOR_PAYMENT, _('Waiting for Payment')),
        (ACCEPT, _('Accept')),
        (ACCEPT_IF, _('Accept with condition')),
        (VOLUNTEER, _("Applicant|Volunteer")),
        (THEY_REFUSED, _("He or she refused")),
    )
    # One of the statuses below could be set after interviewing
    INTERVIEW_RESULTS = {
        ACCEPT,
        ACCEPT_PAID,
        ACCEPT_IF,
        REJECTED_BY_INTERVIEW,
        VOLUNTEER,
        WAITING_FOR_PAYMENT
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
    STUDY_PROGRAMS = (
        (STUDY_PROGRAM_CS, "Computer Science (Современная информатика)"),
        (STUDY_PROGRAM_DS, "Data Science (Анализ данных)"),
        (STUDY_PROGRAM_SE, "Software Engineering (Разработка ПО)")
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
    patronymic = models.CharField(_("Patronymic"), max_length=255,
                                  blank=True, null=True)
    living_place = models.CharField(
        _("Living Place"),
        max_length=255,
        null=True,
        blank=True)
    email = models.EmailField(
        _("Email"),
        help_text=_("Applicant|email"))
    phone = models.CharField(
        _("Contact phone"),
        max_length=42,
        help_text=_("Applicant|phone"))
    stepic_id = models.CharField(
        _("Stepik ID"),
        help_text=_("Applicant|stepic_id"),
        max_length=255,
        blank=True,
        null=True)
    yandex_login = models.CharField(
        _("Yandex Login"),
        max_length=80,
        help_text=_("Applicant|yandex_login"),
        null=True,
        blank=True)
    yandex_login_q = models.CharField(
        _("Yandex Login (normalized)"),
        max_length=80,
        help_text=_("Applicant|yandex_id_normalization"),
        null=True,
        blank=True)
    github_login = models.CharField(
        _("Github Login"),
        max_length=255,
        help_text=_("Applicant|github_login"),
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
    level_of_education = models.CharField(
        _("Course"),
        choices=AcademicDegreeLevels.choices,
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
    online_education_experience = models.TextField(
        _("Online Education Exp"),
        help_text=_("Applicant|online_education_experience"),
        null=True,
        blank=True)
    probability = models.TextField(
        _("Probability"),
        help_text=_("Applicant|probability"),
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
        max_length=255,
        blank=True)
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
    user = models.ForeignKey(
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
        if self.yandex_login:
            self.yandex_login_q = self.yandex_login.lower().replace('-', '.')
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

    def created_local(self, tz=None):
        if not tz:
            tz = self.get_timezone()
        return timezone.localtime(self.created, timezone=tz)

    def get_full_name(self):
        parts = [self.surname, self.first_name, self.patronymic]
        return smart_text(" ".join(part for part in parts if part).strip())

    def clean(self):
        if self.yandex_login:
            self.yandex_login_q = self.yandex_login.lower().replace('-', '.')

    def get_living_place_display(self):
        if not self.living_place and self.campaign.branch.city_id:
            return self.campaign.branch.name
        return self.living_place

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

    def get_similar(self):
        conditions = [
            Q(email=self.email),
            (
                Q(first_name__iexact=self.first_name) &
                Q(surname__iexact=self.surname) &
                Q(patronymic__iexact=self.patronymic)
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


class YandexContestImportResults(NamedTuple):
    on_scoreboard: int
    updated: int


class YandexContestIntegration(models.Model):
    yandex_contest_id = models.CharField(
        _("Contest #ID"),
        help_text=_("Applicant|yandex_contest_id"),
        max_length=42,
        blank=True,
        null=True)
    contest_participant_id = models.IntegerField(
        _("Participant ID"),
        help_text=_("participant_id in Yandex.Contest"),
        null=True,
        blank=True)
    contest_status_code = models.IntegerField(
        "Yandex API Response",
        null=True,
        blank=True)
    status = models.CharField(
        choices=ChallengeStatuses.choices,
        default=ChallengeStatuses.NEW,
        verbose_name=_("Status"),
        help_text=_("Choose `manual score input` to avoid synchronization with "
                    "contest results"),
        max_length=15)

    class Meta:
        abstract = True

    @classmethod
    def check(cls, **kwargs):
        errors = super().check(**kwargs)
        errors.extend(cls._check_applicant_fk())
        return errors

    @classmethod
    def _check_applicant_fk(cls):
        errors = []
        try:
            applicant = cls._meta.get_field("applicant")
            if (not applicant.is_relation or
                    not issubclass(applicant.remote_field.model, Applicant)):
                errors.append(
                    checks.Error(
                        f'`{cls}.applicant` is not a FK to Applicant model',
                        hint='define applicant = OneToOneField(Applicant, ...)',
                        obj=cls,
                        id='admission.E002',
                    ))
        except FieldDoesNotExist:
            errors.append(
                checks.Error(
                    f'`{cls.__name__}` is a subclass of YandexContestIntegration'
                    f' and must define `applicant` field',
                    hint='define applicant = OneToOneField(Applicant, ...)',
                    obj=cls,
                    id='admission.E001',
                ))
        return errors

    def register_in_contest(self, api):
        """
        Registers participant in the contest and saves response
        info (status_code, participant_id)
        """
        applicant = self.applicant
        try:
            status_code, data = api.register_in_contest(applicant.yandex_login,
                                                        self.yandex_contest_id)
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
            registered = (self.__class__.objects
                          .filter(yandex_contest_id=self.yandex_contest_id,
                                  contest_status_code=RegisterStatus.CREATED,
                                  applicant__campaign_id=applicant.campaign_id,
                                  applicant__yandex_login=applicant.yandex_login)
                          .exclude(contest_participant_id__isnull=True)
                          .only("contest_participant_id")
                          .first())
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
        (self.__class__.objects
         .filter(applicant=applicant)
         .update(**update_fields))

    @classmethod
    def import_results(cls, api, contest: Contest) -> YandexContestImportResults:
        """
        Importing contest results page by page.

        Since scoreboard can be modified at any moment we could miss some
        results during the importing if someone has improved his position
        and moved to a scoreboard `page` that has already been processed.
        """
        paging = {
            "page_size": 50,
            "page": 1
        }
        scoreboard_total = 0
        updated_total = 0
        if not contest.details:
            contest.details = {}
        while True:
            try:
                status, json_data = api.standings(contest.contest_id, **paging)
                # XXX: Assignments order on a scoreboard could differ from
                # the similar contest problems API call response
                if "titles" not in contest.details:
                    titles = [t["name"] for t in json_data["titles"]]
                    contest.details["titles"] = titles
                    contest.save(update_fields=("details",))
                page_total = 0
                for row in json_data['rows']:
                    scoreboard_total += 1
                    page_total += 1
                    total_score_str: str = row['score'].replace(',', '.')
                    total_score = int(round(float(total_score_str)))
                    score_details = [a["score"] for a in row["problemResults"]]
                    update_fields = {
                        "score": total_score,
                        "details": {"scores": score_details}
                    }
                    yandex_login = row['participantInfo']['login']
                    participant_id = row['participantInfo']['id']
                    updated = (cls.objects
                               .filter(Q(applicant__yandex_login=yandex_login) |
                                       Q(contest_participant_id=participant_id),
                                       applicant__campaign_id=contest.campaign_id,
                                       yandex_contest_id=contest.contest_id,
                                       status=ChallengeStatuses.REGISTERED)
                               .update(**update_fields))
                    updated_total += updated
                if page_total < paging["page_size"]:
                    break
                paging["page"] += 1
            except YandexContestError as e:
                raise
        return YandexContestImportResults(on_scoreboard=scoreboard_total,
                                          updated=updated_total)


class ApplicantRandomizeContestMixin:
    def compute_contest_id(self, contest_type) -> Optional[int]:
        """
        Returns contest id based on applicant id and existing contest records.
        """
        contests = list(Contest.objects
                        .filter(campaign_id=self.applicant.campaign_id,
                                type=contest_type)
                        .values_list("contest_id", flat=True)
                        .order_by("contest_id"))
        if contests:
            contest_index = self.applicant.id % len(contests)
            return contests[contest_index]


class Test(TimeStampedModel, YandexContestIntegration,
           ApplicantRandomizeContestMixin):
    NEW = ChallengeStatuses.NEW
    REGISTERED = ChallengeStatuses.REGISTERED
    MANUAL = ChallengeStatuses.MANUAL

    applicant = models.OneToOneField(
        Applicant,
        verbose_name=_("Applicant"),
        on_delete=models.PROTECT,
        related_name="online_test")
    score = models.PositiveSmallIntegerField(
        verbose_name=_("Score"), null=True, blank=True)
    details = JSONField(
        verbose_name=_("Details"),
        load_kwargs={'object_pairs_hook': OrderedDict},
        blank=True,
    )

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

    def save(self, **kwargs):
        created = self.pk is None
        if (created and self.status == ChallengeStatuses.NEW and
                not self.yandex_contest_id):
            contest_id = self.compute_contest_id(Contest.TYPE_TEST)
            if contest_id:
                self.yandex_contest_id = contest_id
        super().save(**kwargs)


class Exam(TimeStampedModel, YandexContestIntegration,
           ApplicantRandomizeContestMixin):
    applicant = models.OneToOneField(
        Applicant,
        verbose_name=_("Applicant"),
        on_delete=models.PROTECT,
        related_name="exam")
    score = ScoreField(
        verbose_name=_("Score"),
        # Avoid loading empty values with admin interface
        null=True,
        blank=True)
    details = JSONField(
        verbose_name=_("Details"),
        load_kwargs={'object_pairs_hook': OrderedDict},
        blank=True,
        null=True
    )

    class Meta:
        verbose_name = _("Exam")
        verbose_name_plural = _("Exams")

    def save(self, **kwargs):
        created = self.pk is None
        if (created and self.status == ChallengeStatuses.NEW and
                not self.yandex_contest_id):
            contest_id = self.compute_contest_id(Contest.TYPE_EXAM)
            if contest_id:
                self.yandex_contest_id = contest_id
        super().save(**kwargs)

    def __str__(self):
        """ Import/export get repr before instance created in db."""
        if self.applicant_id:
            return self.applicant.get_full_name()
        else:
            return smart_text(self.score)

    def score_display(self):
        return self.score if self.score is not None else "-"


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


class Interview(TimezoneAwareModel, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = 'applicant'

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

    date = models.DateTimeField(_("When"))
    applicant = models.OneToOneField(
        Applicant,
        verbose_name=_("Applicant"),
        on_delete=models.PROTECT,
        related_name="interview")
    interviewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Interview|Interviewers"),
        limit_choices_to={'group__role': Roles.INTERVIEWER})

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
            tz = self.get_timezone()
        return timezone.localtime(self.date, timezone=tz)

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
            template_name = self.applicant.campaign.template_interview_reminder
            template = get_email_template(template_name)
            (Email.objects
             .filter(template=template, to=self.applicant.email)
             .exclude(status=EMAIL_STATUS.sent)
             .delete())
        except EmailTemplate.DoesNotExist:
            pass

    def delete_feedback(self):
        try:
            template = get_email_template(INTERVIEW_FEEDBACK_TEMPLATE)
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


class InterviewStream(TimezoneAwareModel, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = 'venue'
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
        Location,
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
        limit_choices_to={'group__role': Roles.INTERVIEWER})
    campaign = models.ForeignKey(
        Campaign,
        verbose_name=_("Campaign"),
        on_delete=models.CASCADE,
        related_name="interview_streams")

    class Meta:
        verbose_name = _("Interview stream")
        verbose_name_plural = _("Interview streams")

    def save(self, **kwargs):
        created = self.pk is None
        super().save(**kwargs)
        if created:
            # Generate slots from stream settings
            step = datetime.timedelta(minutes=self.duration)
            slots = [InterviewSlot(start_at=start_at, end_at=end_at, stream=self)
                     for start_at, end_at
                     in slot_range(self.start_at, self.end_at, step)]
            InterviewSlot.objects.bulk_create(slots)

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
        help_text=_("Time in UTC since information about the timezone "
                    "stored in m2m relationship"))
    interview = models.ForeignKey(
        Interview,
        verbose_name=_("Interview"),
        on_delete=models.CASCADE,
        related_name="invitations",
        null=True,
        blank=True)

    objects = InterviewInvitationQuerySet.as_manager()

    class Meta:
        verbose_name = _("Interview invitation")
        verbose_name_plural = _("Interview invitations")

    def save(self, **kwargs):
        created = self.pk is None
        super().save(**kwargs)
        if created and not self.interview_id:
            # Update status if we send invitation before
            # summing up the exam results
            if self.applicant.status == Applicant.PERMIT_TO_EXAM:
                (Applicant.objects
                 .filter(pk=self.applicant_id)
                 .update(status=Applicant.INTERVIEW_TOBE_SCHEDULED))

    def __unicode__(self):
        return str(self.applicant)

    def __str__(self):
        return self.__unicode__()

    @property
    def is_expired(self):
        print(timezone.now())
        return timezone.now() >= self.expired_at

    @property
    def is_accepted(self):
        return bool(self.interview_id)

    def get_absolute_url(self):
        return reverse("admission:interview_appointment", kwargs={
            "year": self.applicant.campaign.year,
            "secret_code": str(self.secret_code).replace("-", "")
        })
