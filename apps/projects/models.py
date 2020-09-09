# -*- coding: utf-8 -*-
import math
import os
from decimal import Decimal
from typing import NamedTuple, Dict

from django.apps import apps
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.db.models import Q, F
from django.utils import timezone, formats
from django.utils.encoding import smart_str
from django.utils.translation import gettext_lazy as _
from djchoices import DjangoChoices, C
from model_utils.models import TimeStampedModel

from core.db.models import ScoreField
from core.mixins import DerivableFieldsMixin
from core.models import LATEX_MARKDOWN_HTML_ENABLED, Branch
from core.timezone import now_local, TimezoneAwareModel
from core.urls import reverse
from core.utils import hashids
from courses.constants import SemesterTypes
from courses.models import Semester
from courses.utils import get_current_term_pair
from files.models import ConfigurableStorageFileField
from files.storage import private_storage
from learning.settings import Branches
from notifications.signals import notify
from projects.constants import ProjectTypes, EDITING_REPORT_COMMENT_AVAIL, ProjectGradeTypes
from users.constants import Roles, GenderTypes

CURATOR_SCORE_FIELDS = [
    "score_quality",
    "score_activity"
]


class ReportingPeriodKey(NamedTuple):
    # FIXME: It should be branch ID now :<
    branch_code: str
    project_type: str


class ReportingPeriodDict(dict):
    def __setitem__(self, key, value):
        if not isinstance(key, ReportingPeriodKey):
            raise TypeError("Key must be ReportingPeriodKey instance")
        if not isinstance(value, (ReportingPeriod, list)):
            raise TypeError("Value must be ReportingPeriod instance or list")
        super().__setitem__(key, value)

    @classmethod
    def from_queryset(cls, queryset):
        """
        Note that this method doesn't take into account date range. You have
        to make sure that queryset for each (branch, project_type) has
        only 1 unique date range or use `first_match=True` by date range
        if queryset data is ordered and target periods go first.
        """
        periods = ReportingPeriodDict()
        for period in queryset:
            branches = []
            if period.branch_id is None:
                # FIXME: restrict by site, code is not unique anymore
                for branch_code, _ in Branches.choices:
                    branches.append(branch_code)
            else:
                branches.append(period.branch.code)
            project_types = [period.project_type]
            if period.project_type is None:
                project_types = [t for t, _ in ProjectTypes.choices]
            for branch_code in branches:
                for project_type in project_types:
                    k = ReportingPeriodKey(branch_code, project_type)
                    if k not in periods:
                        periods[k] = [period]
                    else:
                        # Replace period if new one is more precise
                        same_range_any = False
                        for i, p in enumerate(periods[k]):
                            ranges_eq = (p.start_on == period.start_on and
                                         p.end_on == period.end_on)
                            if ranges_eq and period.weight > p.weight:
                                periods[k][i] = period
                                break
                            elif ranges_eq:
                                same_range_any = True
                        else:
                            if not same_range_any:
                                periods[k].append(period)
        return periods

    def for_branch(self, branch: Branch):
        return {k: v for k, v in self.items() if k.branch_code == branch.code}


class ReportingPeriod(models.Model):
    """
    This model based on assumption that each branch has only 1 (or none)
    active reporting period at a time.
    """
    label = models.CharField(
        verbose_name=_("Label"),
        max_length=150,
        help_text=_("Helps to distinguish student reports for the project."),
        blank=True)
    term = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        verbose_name=_("Semester"),
        related_name="reporting_periods",)
    start_on = models.DateField(
        _("Start On"),
        help_text=_("First day of the report period."))
    end_on = models.DateField(
        _("End On"),
        help_text=_("The last day of the report period."))
    # Note: This field is hidden in admin since it makes logic over complicated
    branch = models.ForeignKey(
        Branch,
        verbose_name=_("Branch"),
        related_name="+",  # Disable backwards relation
        on_delete=models.CASCADE,
        null=True,
        blank=True)
    project_type = models.CharField(
        choices=ProjectTypes.choices,
        verbose_name=_("StudentProject|Type"),
        max_length=10,
        null=True,
        blank=True)
    score_excellent = models.SmallIntegerField(
        _("Min score for EXCELLENT"),
        blank=True,
        null=True,
        help_text=_("Projects with final score >= this value will be "
                    "graded as Excellent"))
    score_good = models.SmallIntegerField(
        _("Min score for GOOD"),
        blank=True,
        null=True,
        help_text=_("Projects with final score in [GOOD; EXCELLENT) will be "
                    "graded as Good."))
    score_pass = models.SmallIntegerField(
        _("Min score for PASS"),
        blank=True,
        null=True,
        help_text=_("Projects with final score in [PASS; GOOD) will be "
                    "graded as Pass, with score < PASS as Unsatisfactory."))

    class Meta:
        verbose_name = _("Reporting Period")
        verbose_name_plural = _("Reporting Periods")
        constraints = [
            models.CheckConstraint(
                check=models.Q(score_excellent__gt=F('score_good')),
                name='good_score_lt_excellent'),
            models.CheckConstraint(
                check=models.Q(score_good__gt=F('score_pass')),
                name='pass_score_lt_good'),
        ]

    def clean(self):
        errors = {}
        if self.start_on and self.end_on and self.start_on > self.end_on:
            errors["end_on"] = "Дата дедлайна меньше даты начала"
        if self.term_id and self.start_on and self.end_on:
            start_utc = self.term.starts_at.date()
            end_utc = self.term.ends_at.date()
            if self.start_on > end_utc or self.start_on < start_utc:
                errors["start_on"] = "Дата начала за пределами указанного семестра"
            if self.end_on > end_utc or self.end_on < start_utc:
                errors["end_on"] = "Дата дедлайна за пределами указанного семестра"
        if errors:
            raise ValidationError(errors)
        # Periods can't be partially overlapped. We could only fully override
        # common period by specifying project type or branch or both.
        if self.start_on and self.end_on:
            overlap = (Q(end_on__gte=self.start_on) &
                       Q(start_on__lte=self.end_on))
            filters = [overlap]
            if self.pk:
                filters.append(~Q(pk=self.pk))
            if self.project_type:
                project_type = (Q(project_type__isnull=True) |
                                Q(project_type=self.project_type))
                filters.append(project_type)
            if self.branch_id:
                branch = Q(branch__isnull=True) | Q(branch_id=self.branch_id)
                filters.append(branch)
            for rp in ReportingPeriod.objects.filter(*filters):
                if rp.start_on != self.start_on or rp.end_on != self.end_on:
                    raise ValidationError(f"Найдено частичное пересечение дат "
                                          f"с отчетным периодом «‎{rp}».")

    def __str__(self):
        start_on = formats.date_format(self.start_on, 'j E')
        end_on = formats.date_format(self.end_on, 'j E')
        parts = []
        if self.project_type:
            parts.append(ProjectTypes.labels[self.project_type].lower())
        if self.branch_id:
            parts.append(self.branch.name)
        suffix = " [" + ", ".join(parts) + "]" if parts else ""
        return f"{self.term}, {start_on}-{end_on}{suffix}"

    def is_started(self, project: "Project"):
        today = now_local(project.branch.get_timezone()).date()
        return today >= self.start_on

    @property
    def weight(self):
        """
        More precise period has more weight. Specifying branch has more
        weight than specifying project_type.
        """
        weight = 0
        weight += 2 if self.branch_id is not None else 0
        weight += int(self.project_type is not None)
        # TODO: Make sure that compared periods have the same date range
        return weight

    @classmethod
    def get_final_periods(cls, term: Semester, *filters) -> ReportingPeriodDict:
        """
        Returns final reporting period for each (branch_code, project_type)
        if any exists.
        """
        qs = (cls.objects
              .filter(Q(term=term), *filters)
              .select_related("branch")
              .order_by('-end_on',
                        F('branch_id').desc(nulls_last=True),
                        F('project_type').desc(nulls_last=True)))
        final_periods = ReportingPeriodDict()
        all_periods = ReportingPeriodDict.from_queryset(qs)
        for k, v in all_periods.items():
            final_periods[k] = v[0]
        return final_periods

    @classmethod
    def get_periods(cls, **filters) -> ReportingPeriodDict:
        qs = (cls.objects
              .filter(**filters)
              .select_related("branch")
              .order_by('-end_on'))
        return ReportingPeriodDict.from_queryset(qs)

    def score_to_grade(self, score, project):
        if score >= self.score_excellent:
            final_grade = ProjectGradeTypes.EXCELLENT
        elif score >= self.score_good:
            final_grade = ProjectGradeTypes.GOOD
        elif score >= self.score_pass:
            final_grade = ProjectGradeTypes.CREDIT
        else:
            final_grade = ProjectGradeTypes.UNSATISFACTORY
        # For external projects use binary grading policy
        if project.is_external and score >= self.score_pass:
            final_grade = ProjectGradeTypes.CREDIT
        return final_grade

    def get_report_form(self, **kwargs):
        from projects.forms import ReportForm
        return ReportForm(initial={"reporting_period": self.id},
                          **kwargs)

    def students_are_notified(self, notification_type, branch: Branch) -> bool:
        from notifications.models import Notification
        notification_type_map = apps.get_app_config('notifications').type_map
        notification_type_id = notification_type_map[notification_type.name]
        actor_content_type = ContentType.objects.get_for_model(self)
        target_content_type = ContentType.objects.get_for_model(branch)
        filters = {
            "type_id": notification_type_id,
            "actor_object_id": self.pk,
            "actor_content_type": actor_content_type,
            "target_object_id": branch.pk,
            "target_content_type": target_content_type
        }
        return Notification.objects.filter(**filters).exists()

    @transaction.atomic
    def generate_notifications(self, notification_type, target_branch: Branch):
        """
        Generate notifications for students without report.
        """
        # FIXME: ProjectStudent should be connected with student_profile instead?
        # Assume student profile is active
        filters = {"student__student_profiles__branch": target_branch}
        if self.project_type is not None:
            filters["project__project_type"] = self.project_type
        project_students = (ProjectStudent.objects
                            .filter(project__semester=self.term,
                                    reports__isnull=True,
                                    **filters)
                            .exclude(final_grade=ProjectGradeTypes.UNSATISFACTORY,
                                     project__status=Project.Statuses.CANCELED)
                            .select_related("student", "project")
                            .distinct()
                            .all())
        context = {
            "start_on": formats.date_format(self.start_on, "SHORT_DATE_FORMAT"),
            "end_on": formats.date_format(self.end_on, "SHORT_DATE_FORMAT"),
        }
        for ps in project_students:
            context.update({
                "project_id": ps.project_id
            })
            notify.send(
                sender=self,  # actor
                type=notification_type,
                verb='was sent',
                target=target_branch,
                recipient=ps.student,
                data=context,)


class ProjectStudent(TimezoneAwareModel, models.Model):
    """Intermediate model for project students"""
    TIMEZONE_AWARE_FIELD_NAME = 'project'
    # TODO: переименовать `GRADES`
    GRADES = ProjectGradeTypes

    student = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE)
    project = models.ForeignKey('Project', on_delete=models.CASCADE)
    supervisor_grade = models.SmallIntegerField(
        verbose_name=_("Supervisor grade"),
        validators=[MinValueValidator(-15), MaxValueValidator(15)],
        help_text=_("Integer value from -15 to 15"),
        blank=True,
        null=True)
    supervisor_review = models.TextField(
        _("Review from supervisor"),
        blank=True)
    presentation_grade = models.PositiveSmallIntegerField(
        verbose_name=_("Presentation grade"),
        validators=[MaxValueValidator(10)],
        help_text=_("Integer value from 0 to 10"),
        blank=True,
        null=True)
    final_grade = models.CharField(
        verbose_name=_("Final grade"),
        choices=GRADES.choices,
        max_length=15,
        default=GRADES.NOT_GRADED)

    class Meta:
        verbose_name = _("Project student")
        verbose_name_plural = _("Project students")
        unique_together = [['student', 'project']]

    def __str__(self):
        return "{0} [{1}]".format(smart_str(self.project),
                                  smart_str(self.student))

    def get_report(self, reporting_period: ReportingPeriod):
        for report in self.reports.all():
            if report.reporting_period_id == reporting_period.pk:
                return report

    @property
    def total_score(self):
        score = 0
        for report in self.reports.all():
            score += report.final_score if report.final_score else 0
        if self.supervisor_grade:
            score += self.supervisor_grade
        if self.presentation_grade:
            score += self.presentation_grade
        return score

    def has_final_grade(self):
        return self.final_grade != self.GRADES.NOT_GRADED

    def final_grade_display(self):
        """
        For internal projects show 'Satisfactory' instead of 'Pass',
        except summer projects.
        For projects earlier spring 2016 (exclusively) -
        dont' override grade status name.

        May hit db to get project and semester instances
        """
        label = self.GRADES.values[self.final_grade]
        # For research work grade type is binary at most
        if self.project.project_type == ProjectTypes.research:
            return label
        # XXX: Assume all projects >= spring 2016 have ids > magic number
        MAGIC_ID = 357
        if (self.final_grade == self.GRADES.CREDIT and
                self.project_id > MAGIC_ID and
                not self.project.is_external and
                self.project.semester.type != SemesterTypes.SUMMER):
            label = _("Assignment|pass")
        return label


def project_presentations_upload_to(self: "Project", filename):
    return "{}/projects/{}/{}/presentations/{}".format(
        self.branch.site_id,
        self.semester.slug,
        self.pk,
        filename)


class Supervisor(models.Model):
    GENDER_MALE = GenderTypes.MALE
    GENDER_FEMALE = GenderTypes.FEMALE
    first_name = models.CharField(
        verbose_name=_("First Name"),
        max_length=45)
    last_name = models.CharField(_('Last Name'), max_length=150)
    patronymic = models.CharField(
        _("Patronymic"),
        max_length=100,
        blank=True)
    occupation = models.CharField(
        _("Workplace"),
        max_length=200,
        blank=True)
    gender = models.CharField(
        _("Gender"),
        max_length=1,
        choices=GenderTypes.choices)

    class Meta:
        verbose_name = _("Supervisor")
        verbose_name_plural = _("Supervisors")

    def __str__(self):
        if self.occupation:
            return f"{self.full_name} /{self.occupation}/"
        return self.full_name

    @property
    def full_name(self):
        parts = (self.first_name, self.patronymic, self.last_name)
        return " ".join(p for p in parts if p).strip()

    def get_abbreviated_name(self, delimiter=chr(160)):  # non-breaking space
        parts = (self.first_name[:1], self.patronymic[:1], self.last_name)
        return smart_str(f".{delimiter}".join(p for p in parts if p).strip())


class ProjectQuerySet(models.QuerySet):
    pass


class _ProjectActiveManager(models.Manager):
    def get_queryset(self):
        return (super().get_queryset()
                .exclude(status=Project.Statuses.CANCELED))


ProjectDefaultManager = models.Manager.from_queryset(ProjectQuerySet)
ProjectActiveManager = _ProjectActiveManager.from_queryset(ProjectQuerySet)


class Project(TimezoneAwareModel, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = 'branch'

    class Statuses(DjangoChoices):
        CANCELED = C('canceled', _("Canceled"))
        CONTINUED = C('continued', _("Continued without intermediate results"))

    name = models.CharField(_("StudentProject|Name"), max_length=255)
    parent = models.ForeignKey(
        'self',
        verbose_name=_("Continuation of Work"),
        help_text=_("Select a project that is the continuation of the current one."),
        on_delete=models.PROTECT,
        blank=True,
        null=True)
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        verbose_name=_("Semester"))
    project_type = models.CharField(
        choices=ProjectTypes.choices,
        verbose_name=_("StudentProject|Type"),
        max_length=10)
    branch = models.ForeignKey(
        Branch,
        verbose_name=_("Branch"),
        related_name="+",  # Disable backwards relation
        on_delete=models.CASCADE)
    is_external = models.BooleanField(
        _("External project"),
        default=False)
    status = models.CharField(
        choices=Statuses.choices,
        verbose_name=_("StudentProject|Status"),
        null=True,
        blank=True,
        max_length=10)
    description = models.TextField(
        _("Description"),
        blank=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Students"),
        through=ProjectStudent)
    reviewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Reviewers"),
        related_name='project_reviewers',
        blank=True,
        # FIXME: replace `is_staff` with CURATOR role
        limit_choices_to=(Q(group__role=Roles.PROJECT_REVIEWER) |
                          Q(is_staff=True)))
    supervisors = models.ManyToManyField(
        Supervisor,
        verbose_name=_("Supervisors"),
        related_name='projects')
    supervisor_presentation = models.FileField(
        _("Supervisor presentation"),
        blank=True,
        max_length=200,
        upload_to=project_presentations_upload_to)
    supervisor_presentation_url = models.URLField(
        _("Link to supervisor presentation"),
        blank=True,
        null=True,
        help_text=_("Supported public link to Yandex.Disk only"))
    supervisor_presentation_slideshare_url = models.URLField(
        _("SlideShare URL for supervisor presentation"), null=True, blank=True)
    presentation = models.FileField(
        _("Participants presentation"),
        blank=True,
        max_length=200,
        upload_to=project_presentations_upload_to)
    presentation_url = models.URLField(
        _("Link to participants presentation"),
        blank=True,
        null=True,
        help_text=_("Supported public link to Yandex.Disk only"))
    presentation_slideshare_url = models.URLField(
        _("SlideShare URL for participants presentation"),
        null=True, blank=True)

    objects = ProjectDefaultManager()
    active = ProjectActiveManager()

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")

    @classmethod
    def from_db(cls, db, field_names, values):
        """
        In post save signal we enqueue task with uploading to slideshare
        if path to presentation file (supervisor or participants)
        has been changed.
        """
        instance = super(Project, cls).from_db(db, field_names, values)
        save_fields = ["presentation", "supervisor_presentation"]
        instance._loaded_values = {k: v for (k, v) in zip(field_names, values)
                                   if k in save_fields}
        return instance

    def __str__(self):
        return f"{self.name}, {self.semester}"

    def get_absolute_url(self):
        return reverse('projects:project_detail', args=[self.pk])

    def get_next_project_url(self):
        return reverse('projects:project_detail_next', args=[self.pk])

    def get_prev_project_url(self):
        return reverse('projects:project_detail_prev', args=[self.pk])

    def get_is_external_display(self):
        return _("Yes") if self.is_external else _("No")

    @property
    def is_canceled(self):
        return self.status == self.Statuses.CANCELED

    def is_active(self):
        """Check project is from current term"""
        term_index = get_current_term_pair(self.branch.get_timezone()).index
        return not self.is_canceled and self.semester.index == term_index


def report_file_upload_to(self: "Report", filename):
    project = self.project_student.project
    return "{}/projects/{}/{}/reports/{}".format(
        project.branch.site_id,
        project.semester.slug,
        project.pk,
        filename)


class Report(TimezoneAwareModel, DerivableFieldsMixin, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = 'project_student'

    SENT = 'sent'
    REVIEW = 'review'
    SUMMARY = 'rating'  # Summarize
    COMPLETED = 'completed'
    # FIXME: django-sfm support for state transitioning
    STATUS = (
        (SENT, _("New Report")),
        (REVIEW, _("Review")),
        (SUMMARY, _("Waiting for final score")),
        (COMPLETED, _("Completed")),

    )

    ACTIVITY = (
        (0, _("Poor commit history")),
        (1, _("Normal activity")),
    )
    QUALITY = (
        (0, _("Bad report quality and unrelated comments")),
        (1, _("Bad report quality, but sensible comments")),
        (2, _("Good report quality and sensible comments")),
    )

    project_student = models.ForeignKey(
        ProjectStudent,
        related_name="reports",
        on_delete=models.PROTECT)
    reporting_period = models.ForeignKey(
        ReportingPeriod,
        related_name="reports",
        on_delete=models.PROTECT)
    status = models.CharField(
        choices=STATUS,
        verbose_name=_("Status"),
        default=SENT,
        max_length=15)
    text = models.TextField(
        _("Description"),
        blank=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    file = ConfigurableStorageFileField(
        _("Report file"),
        blank=True,
        null=True,
        upload_to=report_file_upload_to,
        max_length=200,
        storage=private_storage)
    # curators criteria
    score_activity = models.PositiveSmallIntegerField(
        verbose_name=_("Student activity in cvs"),
        validators=[MaxValueValidator(1)],
        choices=ACTIVITY,
        blank=True,
        null=True
    )
    score_activity_note = models.TextField(
        _("Note for criterion `score_activity`"),
        blank=True, null=True)
    score_quality = models.PositiveSmallIntegerField(
        verbose_name=_("Report's quality"),
        validators=[MaxValueValidator(2)],
        choices=QUALITY,
        blank=True,
        null=True
    )
    score_quality_note = models.TextField(
        _("Note for criterion `score_quality`"),
        blank=True, null=True)
    final_score = ScoreField(
        verbose_name=_("Final Score"),
        null=True,
        blank=True)
    # TODO: Visible to curator and student only
    final_score_note = models.TextField(
        _("Final score note"),
        blank=True,
        null=True)

    derivable_fields = ('final_score',)

    class Meta:
        verbose_name = _("Reports")
        verbose_name_plural = _("Reports")
        unique_together = [('project_student', 'reporting_period')]

    def save(self, *args, **kwargs):
        created = self.pk is None
        if self.status in (Report.SUMMARY, Report.COMPLETED):
            if created:
                self.final_score = 0
            else:
                self.compute_fields("final_score", commit=False)
        super().save(*args, **kwargs)

    def _compute_final_score(self):
        final_score = Decimal(0)
        scores = {}
        reviews = (Review.objects
                   .filter(report=self, is_completed=True)
                   .prefetch_related("criteria"))
        for review in reviews:
            for field_name, score in review.get_scores().items():
                if field_name not in scores:
                    scores[field_name] = (score, 1)
                else:
                    score_sum, reviews_count = scores[field_name]
                    scores[field_name] = (score_sum + score, reviews_count + 1)
        for score_sum, reviews_count in scores.values():
            final_score += math.ceil(score_sum / reviews_count)
        for field_name in CURATOR_SCORE_FIELDS:
            score = getattr(self, field_name)
            final_score += score if score else 0

        if self.final_score != final_score:
            self.final_score = final_score
            return True

        return False

    @property
    def file_name(self):
        if self.file:
            return os.path.basename(self.file.name)

    def file_url(self):
        return reverse("projects:download_report_attachment", kwargs={
            "sid": hashids.encode(self.pk),
            "file_name": self.file_name,
        })

    def __str__(self):
        return smart_str(self.project_student.student)

    def created_local(self, tz=None):
        if not tz:
            tz = self.get_timezone()
        return timezone.localtime(self.created, timezone=tz)

    def get_absolute_url(self):
        """May been inefficient if `project_student` not prefetched """
        return reverse("projects:project_report",
                       kwargs={
                           "project_pk": self.project_student.project_id,
                           "report_id": self.id
                       })

    def get_update_url(self):
        return reverse("projects:project_report_update",
                       kwargs={
                           "project_pk": self.project_student.project_id,
                           "report_id": self.id
                       })

    def get_review_url(self):
        return reverse("projects:project_report_upsert_review",
                       kwargs={
                           "project_pk": self.project_student.project_id,
                           "report_id": self.id
                       })

    @property
    def is_completed(self):
        return self.status == self.COMPLETED


class Review(TimeStampedModel):
    report = models.ForeignKey(Report, on_delete=models.PROTECT)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Project reviewer"),
        on_delete=models.CASCADE)
    # FIXME: remove blank/null if possible
    criteria_content_type = models.ForeignKey(
        ContentType, null=True, blank=True,
        related_name='+', on_delete=models.CASCADE
    )
    criteria_object_id = models.PositiveIntegerField(null=True, blank=True)
    criteria = GenericForeignKey('criteria_content_type', 'criteria_object_id')
    is_completed = models.BooleanField(
        _("Completed"),
        default=False,
        help_text=_("Check if you already completed the assessment."))

    class Meta:
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")
        unique_together = [('report', 'reviewer')]

    def get_scores(self):
        if self.criteria:
            return self.criteria.get_scores()


class CriteriaScoresMixin:
    """
    This mixin helps to calculate Report.final_score mean value
    across all related reviews.
    """
    def get_scores(self) -> Dict:
        """Returns mapping of all score field names to score values"""
        """Returns criteria values"""
        scores = {}
        for field_name in self.SCORE_FIELDS:
            score = getattr(self, field_name)
            if score is None:
                score = 0
            scores[field_name] = score
        return scores


# TODO: Add check that CriteriaScoresMixin subclass define SCORE_FIELDS
class PracticeCriteria(CriteriaScoresMixin, models.Model):
    SCORE_FIELDS = (
        "score_global_issue",
        "score_usefulness",
        "score_progress",
        "score_problems",
        "score_technologies",
        "score_plans",
    )

    GLOBAL_ISSUE_CRITERION = (
        (0, _("0 - Does not understand the task at all")),
        (1, _("1 - Understands, but very superficial")),
        (2, _("2 - Understands everything"))
    )

    USEFULNESS_CRITERION = (
        (0, _("0 - Does not understand")),
        (1, _("1 - Writing something about the usefulness")),
        (2, _("2 - Understands and explains"))
    )

    PROGRESS_CRITERION = (
        (0, _("0 - Understand only theory, or even less")),
        (1, _("1 - Some progress, but not enough")),
        (2, _("2 - The normal rate of work"))
    )

    PROBLEMS_CRITERION = (
        (0, _("0 - Problems not mentioned in the report")),
        (1, _("1 - Problems are mentioned without any details")),
        (2, _("2 - Problems are mentioned and explained how they been solved"))
    )

    TECHNOLOGIES_CRITERION = (
        (0, _("0 - Listed, but not explained why.")),
        (1, _("1 - The student does not understand about everything and "
              "does not try to understand, but knows something")),
        (2, _("2 - Understands why choose one or the other technology"))
    )

    PLANS_CRITERION = (
        (0, _("0 - Much less than what has already been done, or the student "
              "does not understand them")),
        (1, _("1 - It seems to have plans of normal size, but does not "
              "understand what to do.")),
        (2, _("2 - All right with them"))
    )

    review = models.ForeignKey(
        Review,
        verbose_name=_("Review"),
        related_name="+",
        on_delete=models.CASCADE)
    score_global_issue = models.PositiveSmallIntegerField(
        choices=GLOBAL_ISSUE_CRITERION,
        verbose_name=_("The global task for term"),
        blank=True,
        null=True
    )
    score_usefulness = models.PositiveSmallIntegerField(
        choices=USEFULNESS_CRITERION,
        verbose_name=_("Possible uses and scenarios"),
        blank=True,
        null=True
    )
    score_progress = models.PositiveSmallIntegerField(
        choices=PROGRESS_CRITERION,
        verbose_name=_("What has been done since the start of the project."),
        blank=True,
        null=True
    )
    score_problems = models.PositiveSmallIntegerField(
        choices=PROBLEMS_CRITERION,
        verbose_name=_("What problems have arisen in the process."),
        blank=True,
        null=True
    )
    score_technologies = models.PositiveSmallIntegerField(
        choices=TECHNOLOGIES_CRITERION,
        verbose_name=_("The choice of technologies or method of integration "
                       "with the existing development"),
        blank=True,
        null=True
    )
    score_plans = models.PositiveSmallIntegerField(
        choices=PLANS_CRITERION,
        verbose_name=_("Future plan"),
        blank=True,
        null=True
    )
    score_global_issue_note = models.TextField(
        _("Note for criterion #1"),
        blank=True, null=True)

    score_usefulness_note = models.TextField(
        _("Note for criterion #2"),
        blank=True, null=True)

    score_progress_note = models.TextField(
        _("Note for criterion #3"),
        blank=True, null=True)

    score_problems_note = models.TextField(
        _("Note for criterion #4"),
        blank=True, null=True)

    score_technologies_note = models.TextField(
        _("Note for criterion #5"),
        blank=True, null=True)

    score_plans_note = models.TextField(
        _("Note for criterion #6"),
        blank=True,
        null=True)

    class Meta:
        verbose_name = _("Practice Criteria")
        verbose_name_plural = _("Practice Criteria")


def report_comment_attachment_upload_to(self: "ReportComment", filename):
    return "{}/projects/{}/{}/attachments/{}".format(
        self.report.project_student.project.branch.site_id,
        self.report.project_student.project.semester.slug,
        self.report.project_student.project.pk,
        filename
    )


class ReportComment(TimezoneAwareModel, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = 'report'

    report = models.ForeignKey(Report, on_delete=models.PROTECT)
    text = models.TextField(
        _("ReportComment|text"),
        help_text=_("LaTeX+Markdown is enabled"),
        blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Author"),
        on_delete=models.CASCADE)
    attached_file = ConfigurableStorageFileField(
        upload_to=report_comment_attachment_upload_to,
        storage=private_storage,
        max_length=200,
        blank=True)

    class Meta:
        ordering = ["created"]
        verbose_name = _("Report comment")
        verbose_name_plural = _("Report comments")

    def __str__(self):
        return ("Comment to {0} by {1}"
                .format(smart_str(self.report),
                        smart_str(self.author.get_full_name())))

    def created_local(self, tz=None):
        if not tz:
            tz = self.get_timezone()
        return timezone.localtime(self.created, timezone=tz)

    @property
    def is_stale_for_editing(self):
        """Editing comment is available for 10 min period only"""
        diff = timezone.now() - self.created
        return diff.total_seconds() > EDITING_REPORT_COMMENT_AVAIL

    @property
    def attached_file_name(self):
        return os.path.basename(self.attached_file.name)

    def get_attachment_download_url(self):
        return reverse("projects:download_report_comment_attachment", kwargs={
            "sid": hashids.encode(self.pk),
            "file_name": self.attached_file_name,
        })
