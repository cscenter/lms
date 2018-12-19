# -*- coding: utf-8 -*-

import math
import os

from django.apps import apps
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible, smart_text
from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, ChoiceItem
from model_utils.models import TimeStampedModel

from core.models import LATEX_MARKDOWN_HTML_ENABLED, City
from core.utils import hashids
from courses.models import Semester
from learning.settings import AcademicRoles, GradeTypes
from courses.settings import SemesterTypes
from core.timezone import now_local
from courses.utils import get_current_term_index

# Calculate mean scores for these fields when review has been completed
REVIEW_SCORE_FIELDS = [
    "score_global_issue",
    "score_usefulness",
    "score_progress",
    "score_problems",
    "score_technologies",
    "score_plans",
]

CURATOR_SCORE_FIELDS = [
    "score_quality",
    "score_activity"
]


class ProjectStudent(models.Model):
    """Intermediate model for project students"""
    # TODO: переименовать `GRADES`, создать ProjectGradeTypes (в settings.py)
    GRADES = GradeTypes
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
        return "{0} [{1}]".format(smart_text(self.project),
                                  smart_text(self.student))

    def get_city(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city()

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city_timezone()

    @property
    def city_aware_field_name(self):
        return self.__class__.project.field.name

    def get_report_url(self):
        return reverse(
            "projects:student_project_report",
            kwargs={
                "project_pk": self.project.pk,
                "student_pk": self.student.pk
            }
        )

    @property
    def total_score(self):
        acc = 0
        for attr in (self.supervisor_grade, self.presentation_grade):
            try:
                acc += int(attr)
            except (TypeError, ValueError):
                continue
        try:
            acc += int(self.report.final_score)
        except (TypeError, ValueError, ObjectDoesNotExist):
            pass
        return acc

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
        if self.project.project_type == Project.ProjectTypes.research:
            return label
        # XXX: Assume all projects >= spring 2016 have id > magic number
        MAGIC_ID = 357
        if (self.final_grade == self.GRADES.CREDIT and
                self.project_id > MAGIC_ID and
                not self.project.is_external and
                self.project.semester.type != SemesterTypes.SUMMER):
            label = _("Assignment|pass")
        return label


def project_presentation_files(self, filename):
    return os.path.join('projects',
                        '{}-{}'.format(self.semester.year, self.semester.type),
                        '{}'.format(self.pk),
                        'presentations',
                        filename)


class Project(TimeStampedModel):
    class ProjectTypes(DjangoChoices):
        practice = ChoiceItem('practice', _("StudentProject|Practice"))
        research = ChoiceItem('research', _("StudentProject|Research"))

    name = models.CharField(_("StudentProject|Name"), max_length=255)
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
        limit_choices_to=(Q(groups=AcademicRoles.PROJECT_REVIEWER) |
                          Q(is_superuser=True))
    )
    supervisor = models.CharField(
        verbose_name=_("StudentProject|Supervisor"),
        max_length=255,
        help_text=_("Format: Last_name First_name Patronymic, Organization"))
    supervisor_presentation = models.FileField(
        _("Supervisor presentation"),
        blank=True,
        upload_to=project_presentation_files)
    supervisor_presentation_url = models.URLField(
        _("Link to supervisor presentation"),
        blank=True,
        null=True,
        help_text=_("Supported public link to Yandex.Disk only"))
    supervisor_presentation_slideshare_url = models.URLField(
        _("SlideShare URL for supervisor presentation"), null=True, blank=True)
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        verbose_name=_("Semester"))
    project_type = models.CharField(
        choices=ProjectTypes.choices,
        verbose_name=_("StudentProject|Type"),
        max_length=10)
    presentation = models.FileField(
        _("Participants presentation"),
        blank=True,
        upload_to=project_presentation_files)
    presentation_url = models.URLField(
        _("Link to participants presentation"),
        blank=True,
        null=True,
        help_text=_("Supported public link to Yandex.Disk only"))
    presentation_slideshare_url = models.URLField(
        _("SlideShare URL for participants presentation"),
        null=True, blank=True)
    city = models.ForeignKey(City, verbose_name=_("City"),
                             default=settings.DEFAULT_CITY_CODE,
                             on_delete=models.CASCADE)
    is_external = models.BooleanField(
        _("External project"),
        default=False)
    canceled = models.BooleanField(
        default=False,
        help_text=_("Check if all participants leave project before "
                    "reporting period"))

    class Meta:
        verbose_name = _("Student project")
        verbose_name_plural = _("Student projects")

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
        return smart_text(self.name)

    def get_city(self):
        return self.city_id

    def get_city_timezone(self):
        return settings.TIME_ZONES[self.city_id]

    @property
    def city_aware_field_name(self):
        return self.__class__.city.field.name

    def get_absolute_url(self):
        return reverse('projects:project_detail', args=[self.pk])

    def get_is_external_display(self):
        return _("Yes") if self.is_external else _("No")

    def is_active(self):
        """Check project is from current term"""
        current_term_index = get_current_term_index(self.city_id)
        return not self.canceled and self.semester.index == current_term_index

    def report_period_started(self):
        if not self.semester.report_starts_at:
            return False
        today = now_local(self.city_id).date()
        return today >= self.semester.report_starts_at

    def report_period_ended(self):
        today = now_local(self.city_id).date()
        if not self.semester.report_ends_at:
            return None
        return self.semester.report_ends_at > today

    def report_period_active(self):
        semester = self.semester
        if not semester.report_starts_at or not semester.report_ends_at:
            return False
        today = now_local(self.city_id).date()
        return semester.report_starts_at <= today <= semester.report_ends_at


class ReviewCriteria(TimeStampedModel):
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

    score_global_issue = models.PositiveSmallIntegerField(
        choices=GLOBAL_ISSUE_CRITERION,
        verbose_name=_("The global task for term"),
        blank=True,
        null=True
    )
    score_usefulness = models.PositiveSmallIntegerField(
        choices=USEFULNESS_CRITERION,
        verbose_name=_("Who and why this can be useful."),
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
        verbose_name=_("What technologies are used."),
        blank=True,
        null=True
    )
    score_plans = models.PositiveSmallIntegerField(
        choices=PLANS_CRITERION,
        verbose_name=_("Future plan"),
        blank=True,
        null=True
    )

    class Meta:
        abstract = True


def report_file_name(self, filename):
    return os.path.join('projects',
                        '{}-{}'.format(
                            self.project_student.project.semester.year,
                            self.project_student.project.semester.type),
                        '{}'.format(self.project_student.project.pk),
                        'reports',
                        filename)


@python_2_unicode_compatible
class Report(ReviewCriteria):
    SENT = 'sent'
    REVIEW = 'review'
    SUMMARY = 'rating'  # Summarize
    COMPLETED = 'completed'
    STATUS = (
        (SENT, _("Sent")),
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

    project_student = models.OneToOneField(ProjectStudent, on_delete=models.PROTECT)
    status = models.CharField(
        choices=STATUS,
        verbose_name=_("Status"),
        default=SENT,
        max_length=15)
    text = models.TextField(
        _("Description"),
        blank=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    file = models.FileField(
        _("Report file"),
        blank=True,
        null=True,
        upload_to=report_file_name)
    # curators only below
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

    @property
    def file_name(self):
        if self.file:
            return os.path.basename(self.file.name)

    def file_url(self):
        return reverse(
            "projects:report_attachments_download",
            args=[
                hashids.encode(
                    apps.get_app_config("projects").REPORT_ATTACHMENT,
                    self.pk
                )]
        )

    # TODO: Visible to curator and student only
    final_score_note = models.TextField(
        _("Final score note"),
        blank=True,
        null=True)

    class Meta:
        verbose_name = _("Reports")
        verbose_name_plural = _("Reports")

    def __str__(self):
        return smart_text(self.project_student.student)

    def get_city(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city()

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city_timezone()

    @property
    def city_aware_field_name(self):
        return self.__class__.project_student.field.name

    def created_local(self, tz=None):
        if not tz:
            tz = self.get_city_timezone()
        return timezone.localtime(self.created, timezone=tz)

    def get_absolute_url(self):
        """May been inefficient if `project_student` not prefetched """
        return reverse("projects:project_report", kwargs={
            "project_pk": self.project_student.project_id,
            "student_pk": self.project_student.student_id
        })

    def review_state(self):
        return self.status == self.REVIEW

    def summarize_state(self):
        return self.status == self.SUMMARY

    def is_completed(self):
        return self.status == self.COMPLETED

    def calculate_mean_scores(self):
        """Set mean values on score fields which been assessed by reviewers"""
        scores = {field_name: (0, 0) for field_name in REVIEW_SCORE_FIELDS}
        for review in self.review_set.all():
            for field_name in REVIEW_SCORE_FIELDS:
                total, count = scores[field_name]
                if getattr(review, field_name) is not None:
                    scores[field_name] = (
                        total + getattr(review, field_name),
                        count + 1
                    )
        for field_name in REVIEW_SCORE_FIELDS:
            total, count = scores.get(field_name)
            mean = math.ceil(total / count) if count else 0
            setattr(self, field_name, mean)

    @property
    def final_score(self):
        """Sum of all criteria"""
        if not self.is_completed():
            return _("review not completed")
        return self.calculate_final_score()

    def calculate_final_score(self):
        """For preliminary assessment call calculate_mean_scores first"""
        return sum(
            getattr(self, field.name) for field in self._meta.get_fields()
            if isinstance(field, models.IntegerField) and
            field.name.startswith("score_") and
            getattr(self, field.name) is not None
        )


@python_2_unicode_compatible
class Review(ReviewCriteria):
    report = models.ForeignKey(Report, on_delete=models.PROTECT)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Project reviewer"),
        on_delete=models.CASCADE)

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

    is_completed = models.BooleanField(
        _("Completed"),
        default=False,
        help_text=_("Check if you already completed the assessment."))

    class Meta:
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")
        unique_together = [('report', 'reviewer')]


def report_comment_attachment_upload_to(self, filename):
    return "projects/{}-{}/{}/attachments/{}".format(
        self.report.project_student.project.semester.year,
        self.report.project_student.project.semester.type,
        self.report.project_student.project.pk,
        filename
    )


@python_2_unicode_compatible
class ReportComment(TimeStampedModel):
    report = models.ForeignKey(Report, on_delete=models.PROTECT)
    text = models.TextField(
        _("ReportComment|text"),
        help_text=_("LaTeX+Markdown is enabled"),
        blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Author"),
        on_delete=models.CASCADE)
    attached_file = models.FileField(
        upload_to=report_comment_attachment_upload_to,
        blank=True)

    class Meta:
        ordering = ["created"]
        verbose_name = _("Report comment")
        verbose_name_plural = _("Report comments")

    def __str__(self):
        return ("Comment to {0} by {1}"
                .format(smart_text(self.report),
                        smart_text(self.author.get_full_name())))

    def get_city(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city()

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city_timezone()

    @property
    def city_aware_field_name(self):
        return self.__class__.report.field.name

    def created_local(self, tz=None):
        if not tz:
            tz = self.get_city_timezone()
        return timezone.localtime(self.created, timezone=tz)

    @property
    def attached_file_name(self):
        return os.path.basename(self.attached_file.name)

    def attached_file_url(self):
        return reverse(
            "projects:report_attachments_download",
            args=[hashids.encode(
                apps.get_app_config("projects").REPORT_COMMENT_ATTACHMENT,
                self.pk
            )]
        )
