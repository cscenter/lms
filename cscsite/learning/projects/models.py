# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import os.path

from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.encoding import python_2_unicode_compatible, smart_text
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from model_utils.models import TimeStampedModel

from core.models import LATEX_MARKDOWN_HTML_ENABLED
from learning.models import Semester
from learning.settings import GRADES, PARTICIPANT_GROUPS


def project_slides_file_name(self, filename):
    return os.path.join('projects',
                        '{}-{}'.format(self.semester.year, self.semester.type),
                        # FIXME: think how to remove id
                        self.pk,
                        'presentation',
                        filename)


@python_2_unicode_compatible
class ProjectStudent(models.Model):
    """Intermediate model for project students"""
    GRADES = GRADES
    student = models.ForeignKey(settings.AUTH_USER_MODEL)
    project = models.ForeignKey('Project')
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
        choices=GRADES,
        max_length=15,
        default=GRADES.not_graded)

    class Meta:
        verbose_name = _("Project student")
        verbose_name_plural = _("Project students")
        unique_together = [['student', 'project']]

    def __str__(self):
        return "{0} [{1}]".format(smart_text(self.project),
                                  smart_text(self.student))


@python_2_unicode_compatible
class Project(TimeStampedModel):
    GRADES = GRADES
    PROJECT_TYPES = Choices(('practice', _("StudentProject|Practice")),
                            ('research', _("StudentProject|Research")))

    name = models.CharField(_("StudentProject|Name"), max_length=255)
    description = models.TextField(
        _("Description"),
        blank=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Students"),
        # XXX: Admin view can generate duplicates if user has both groups
        limit_choices_to={'groups__in': [PARTICIPANT_GROUPS.STUDENT_CENTER,
                                         PARTICIPANT_GROUPS.GRADUATE_CENTER]},
        through=ProjectStudent)
    reviewers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Reviewers"),
        related_name='project_reviewers',
        blank=True,
        limit_choices_to={'groups': PARTICIPANT_GROUPS.PROJECT_REVIEWER},)
    supervisor = models.CharField(
        verbose_name=_("StudentProject|Supervisor"),
        max_length=255,
        help_text=_("Format: Last_name First_name Patronymic, Organization"))
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        verbose_name=_("Semester"))
    project_type = models.CharField(
        choices=PROJECT_TYPES,
        verbose_name=_("StudentProject|Type"),
        max_length=10)
    presentation = models.FileField(
        _("Presentation"),
        blank=True,
        upload_to=project_slides_file_name)
    is_external = models.BooleanField(
        _("External project"),
        default=False)

    class Meta:
        verbose_name = _("Student project")
        verbose_name_plural = _("Student projects")

    def __str__(self):
        return smart_text(self.name)


class ReviewCriteria(TimeStampedModel):
    GLOBAL_ISSUE_CRITERION = (
        (0, _("Does not understand the task at all")),
        (1, _("Understands, but very superficial")),
        (2, _("Understands everything"))
    )

    USEFULNESS_CRITERION = (
        (0, _("Does not understand")),
        (1, _("Writing something about the usefulness")),
        (2, _("Understands and explains"))
    )

    PROGRESS_CRITERION = (
        (0, _("Understand only theory, or even less")),
        (1, _("Some progress, but not enough")),
        (2, _("The normal rate of work"))
    )

    PROBLEMS_CRITERION = (
        (0, _("Problems not mentioned in the report")),
        (1, _("Problems are mentioned without any details")),
        (2, _("Problems are mentioned and explained how they been solved"))
    )

    TECHNOLOGIES_CRITERION = (
        (0, _("Listed, but not explained why.")),
        (1, _("The student does not understand about everything and "
              "does not try to understand, but knows something")),
        (2, _("Understands why choose one or the other technology"))
    )

    PLANS_CRITERION = (
        (0, _("Much less than what has already been done, or the student "
              "does not understand them")),
        (1, _("It seems to have plans of normal size, but does not "
              "understand what to do.")),
        (2, _("All right with them"))
    )

    score_global_issue = models.PositiveSmallIntegerField(
        choices=GLOBAL_ISSUE_CRITERION,
        verbose_name=_("The global task for term"),
        help_text=_("Criterion #1"),
        blank=True,
        null=True
    )
    score_global_issue_note = models.TextField(
        _("Note for criterion #1"),
        blank=True, null=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    score_usefulness = models.PositiveSmallIntegerField(
        choices=USEFULNESS_CRITERION,
        verbose_name=_("Who and why this can be useful."),
        help_text=_("Criterion #2"),
        blank=True,
        null=True
    )
    score_usefulness_note = models.TextField(
        _("Note for criterion #2"),
        blank=True, null=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    score_progress = models.PositiveSmallIntegerField(
        choices=PROGRESS_CRITERION,
        verbose_name=_("What has been done since the start of the project."),
        help_text=_("Criterion #3"),
        blank=True,
        null=True
    )
    score_progress_note = models.TextField(
        _("Note for criterion #3"),
        blank=True, null=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    score_problems = models.PositiveSmallIntegerField(
        choices=PROBLEMS_CRITERION,
        verbose_name=_("What problems have arisen in the process."),
        help_text=_("Criterion #4"),
        blank=True,
        null=True
    )
    score_problems_note = models.TextField(
        _("Note for criterion #4"),
        blank=True, null=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    score_technologies = models.PositiveSmallIntegerField(
        choices=TECHNOLOGIES_CRITERION,
        verbose_name=_("What technologies are used."),
        help_text=_("Criterion #5"),
        blank=True,
        null=True
    )
    score_technologies_note = models.TextField(
        _("Note for criterion #5"),
        blank=True, null=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    score_plans = models.PositiveSmallIntegerField(
        choices=PLANS_CRITERION,
        verbose_name=_("Future plan"),
        help_text=_("Criterion #6"),
        blank=True,
        null=True
    )
    score_plans_note = models.TextField(
        _("Note for criterion #6"),
        blank=True,
        null=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)

    class Meta:
        abstract = True


# FIXME: prevent unauthorized download!
def report_file_name(self, filename):
    return os.path.join('projects',
                        '{}-{}'.format(self.semester.year, self.semester.type),
                        # FIXME: remove id?
                        self.student.project.pk,
                        'reports',
                        filename)


@python_2_unicode_compatible
class Report(ReviewCriteria):
    SENT = 'sent'  # TODO: send notification, whet report was created
    REVIEW = 'review'
    RATING = 'rating'  # Waiting for curator's final score
    COMPLETED = 'completed'
    STATUS = (
        (SENT, _("Sent")),
        (REVIEW, _("Review")),
        (RATING, _("Waiting for final score")),
        (COMPLETED, _("Completed")),

    )

    project_student = models.OneToOneField(ProjectStudent)
    status = models.CharField(
        choices=STATUS,
        verbose_name=_("Status"),
        default=SENT,
        max_length=15)
    description = models.TextField(
        _("Description"),
        blank=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    file = models.FileField(
        _("Report file"),
        blank=True,
        null=True,
        upload_to=report_file_name)
    # curators only criteria
    score_activity = models.PositiveSmallIntegerField(
        verbose_name=_("Student activity in cvs"),
        validators=[MaxValueValidator(1)],
        default=0,
        blank=True,
        null=True
    )
    score_quality = models.PositiveSmallIntegerField(
        verbose_name=_("Report's quality"),
        validators=[MaxValueValidator(2)],
        default=0,
        blank=True,
        null=True
    )
    # TODO: Visible to curator and student only
    final_score_note = models.TextField(
        _("Final score note"),
        blank=True,
        null=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)

    class Meta:
        verbose_name = _("Reports")
        verbose_name_plural = _("Reports")

    def __str__(self):
        return smart_text(self.project_student.student)

    @property
    def final_score(self):
        """Sum of all criteria"""
        return sum(getattr(self, field.name) for field in self._meta.fields()
                   if isinstance(field, models.IntegerField)
                   and field.name.startswith("score_"))


@python_2_unicode_compatible
class Review(ReviewCriteria):
    report = models.ForeignKey(Report)
    # TODO: Dynamically set `is_completed` before save or calc at runtime
    is_completed = models.BooleanField(_("Completed"), default=False)

    class Meta:
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")
