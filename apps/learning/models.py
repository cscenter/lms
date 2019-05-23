# -*- coding: utf-8 -*-

import logging
import os.path

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.encoding import smart_text
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, ChoiceItem
from model_utils.fields import MonitorField
from model_utils.managers import QueryManager
from model_utils.models import TimeStampedModel

from core.db.models import ScoreField
from core.models import LATEX_MARKDOWN_HTML_ENABLED, City
from core.urls import reverse
from core.utils import hashids
from courses.models import Course, CourseNews, Venue, \
    Assignment
from learning import settings as learn_conf
from learning.managers import EnrollmentDefaultManager, \
    EnrollmentActiveManager, EventQuerySet, StudentAssignmentManager
from learning.settings import GradingSystems, GradeTypes, Branches, \
    AcademicDegreeYears

logger = logging.getLogger(__name__)


class StudentProfile(models.Model):
    enrollment_year = models.PositiveSmallIntegerField(
        _("CSCUser|enrollment year"),
        validators=[MinValueValidator(1990)],
        blank=True,
        null=True)
    graduation_year = models.PositiveSmallIntegerField(
        _("CSCUser|graduation year"),
        blank=True,
        validators=[MinValueValidator(1990)],
        null=True)
    curriculum_year = models.PositiveSmallIntegerField(
        _("CSCUser|Curriculum year"),
        validators=[MinValueValidator(2000)],
        blank=True,
        null=True)
    branch = models.ForeignKey(
        "learning.Branch",
        verbose_name=_("Branch"),
        related_name="+",  # Disable backwards relation
        on_delete=models.SET_NULL,
        null=True,
        blank=True)
    university = models.CharField(
        _("University"),
        max_length=255,
        blank=True)
    phone = models.CharField(
        _("Phone"),
        max_length=40,
        blank=True)
    uni_year_at_enrollment = models.CharField(
        _("StudentInfo|University year"),
        choices=AcademicDegreeYears.choices,
        max_length=2,
        help_text=_("at enrollment"),
        null=True,
        blank=True)
    areas_of_study = models.ManyToManyField(
        'study_programs.AcademicDiscipline',
        verbose_name=_("StudentInfo|Areas of study"),
        blank=True)

    class Meta:
        abstract = True


class Branch(models.Model):
    code = models.CharField(
        _("Code"),
        choices=Branches.choices,
        max_length=8,
        unique=True)
    name = models.CharField(_("Branch|Name"), max_length=255)
    is_remote = models.BooleanField(_("Distance Branch"), default=False)
    description = models.TextField(
        _("Description"),
        help_text=_("Branch|Description"),
        blank=True)

    class Meta:
        verbose_name = _("Branch")
        verbose_name_plural = _("Branches")

    def __str__(self):
        return self.name

    @property
    def timezone(self):
        return Branches.get_choice(self.code).timezone

    @property
    def abbr(self):
        return Branches.get_choice(self.code).abbr


class Enrollment(TimeStampedModel):
    GRADES = GradeTypes
    objects = EnrollmentDefaultManager()
    active = EnrollmentActiveManager()

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Student"),
        on_delete=models.CASCADE)
    course = models.ForeignKey(
        Course,
        verbose_name=_("Course offering"),
        on_delete=models.CASCADE)
    grade = models.CharField(
        verbose_name=_("Enrollment|grade"),
        max_length=100,
        choices=GradeTypes.choices,
        default=GradeTypes.NOT_GRADED)
    grade_changed = MonitorField(
        verbose_name=_("Enrollment|grade changed"),
        monitor='grade')
    is_deleted = models.BooleanField(
        _("The student left the course"),
        default=False)
    reason_entry = models.TextField(
        _("Entry reason"),
        blank=True)
    reason_leave = models.TextField(
        _("Leave reason"),
        blank=True)

    class Meta:
        ordering = ("student", "course")
        unique_together = [('student', 'course')]
        verbose_name = _("Enrollment")
        verbose_name_plural = _("Enrollments")

    def __str__(self):
        return "{0} - {1}".format(smart_text(self.course),
                                  smart_text(self.student.get_full_name()))

    def clean(self):
        if not self.student.is_student:
            raise ValidationError(_("Only students can enroll to courses"))

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)
        # TODO: Call on changing `is_deleted` flag only
        self._populate_assignments_for_new_enrolled_student(created)

    def _populate_assignments_for_new_enrolled_student(self, created):
        if self.is_deleted:
            return
        for a in self.course.assignment_set.all():
            StudentAssignment.objects.get_or_create(assignment=a,
                                                    student_id=self.student_id)

    def get_city(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city()

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city_timezone()

    @property
    def city_aware_field_name(self):
        return self.__class__.course.field.name

    def grade_changed_local(self, tz=None):
        if not tz:
            tz = self.get_city_timezone()
        return timezone.localtime(self.grade_changed, timezone=tz)

    @property
    def grade_display(self):
        return self.GRADES.values[self.grade]

    @property
    def grade_honest(self):
        """Show `satisfactory` instead of `pass` for default grading type"""
        if (self.course.grading_type == GradingSystems.BASE and
                self.grade == self.GRADES.CREDIT):
            return _("Satisfactory")
        return self.GRADES.values[self.grade]


class StudentAssignment(TimeStampedModel):
    class CommentAuthorTypes(DjangoChoices):
        NOBODY = ChoiceItem(0)
        STUDENT = ChoiceItem(1)
        TEACHER = ChoiceItem(2)

    class States(DjangoChoices):
        NOT_SUBMITTED = ChoiceItem(
            "not_submitted", _("Assignment|not submitted"),
            abbr="—", css_class="not-submitted")
        NOT_CHECKED = ChoiceItem(
            "not_checked", _("Assignment|not checked"),
            abbr="…", css_class="not-checked")
        UNSATISFACTORY = ChoiceItem(
            "unsatisfactory", _("Assignment|unsatisfactory"),
            abbr="2", css_class="unsatisfactory")
        CREDIT = ChoiceItem(
            "pass", _("Assignment|pass"),
            abbr="3", css_class="pass")
        GOOD = ChoiceItem(
            "good", _("Assignment|good"),
            abbr="4", css_class="good")
        EXCELLENT = ChoiceItem(
            "excellent", _("Assignment|excellent"),
            abbr="5", css_class="excellent")

    assignment = models.ForeignKey(
        Assignment,
        verbose_name=_("StudentAssignment|assignment"),
        on_delete=models.CASCADE)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("StudentAssignment|student"),
        on_delete=models.CASCADE)
    score = ScoreField(
        verbose_name=_("Grade"),
        null=True,
        blank=True)
    score_changed = MonitorField(
        verbose_name=_("Assignment|grade changed"),
        monitor='score')
    first_student_comment_at = models.DateTimeField(
        _("First Student Comment At"),
        null=True,
        editable=False)
    # TODO: rename
    last_comment_from = models.PositiveSmallIntegerField(
        verbose_name=_("The author type of the latest comment"),
        editable=False,
        choices=CommentAuthorTypes.choices,
        default=CommentAuthorTypes.NOBODY)

    objects = StudentAssignmentManager()

    class Meta:
        ordering = ["assignment", "student"]
        verbose_name = _("Assignment-student")
        verbose_name_plural = _("Assignment-students")
        unique_together = [['assignment', 'student']]

    def clean(self):
        if not self.student.is_student:
            raise ValidationError(_("Student field should point to "
                                    "an actual student"))
        if self.score and self.score > self.assignment.maximum_score:
            raise ValidationError(_("Grade can't be larger than maximum "
                                    "one ({0})")
                                  .format(self.assignment.maximum_score))

    def __str__(self):
        return "{0} - {1}".format(smart_text(self.assignment),
                                  smart_text(self.student.get_full_name()))

    def get_city(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city()

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city_timezone()

    @property
    def city_aware_field_name(self):
        return self.__class__.assignment.field.name

    def get_teacher_url(self):
        return reverse('teaching:student_assignment_detail',
                       kwargs={"pk": self.pk})

    def get_student_url(self):
        return reverse('study:student_assignment_detail',
                       kwargs={"pk": self.pk})

    def has_unread(self):
        from notifications.middleware import get_unread_notifications_cache
        cache = get_unread_notifications_cache()
        return self.pk in cache.assignments

    def has_comments(self, user):
        return any(c.author_id == user.pk for c in
                   self.assignmentcomment_set.all())

    @cached_property
    def state(self):
        score = self.score
        passing_score = self.assignment.passing_score
        maximum_score = self.assignment.maximum_score
        satisfactory_range = maximum_score - passing_score
        if score is None:
            if not self.assignment.is_online or self.submission_is_received:
                state = StudentAssignment.States.NOT_CHECKED
            else:
                state = StudentAssignment.States.NOT_SUBMITTED
        else:
            if score < passing_score or score == 0:
                state = StudentAssignment.States.UNSATISFACTORY
            elif score < passing_score + 0.4 * satisfactory_range:
                state = StudentAssignment.States.CREDIT
            elif score < passing_score + 0.8 * satisfactory_range:
                state = StudentAssignment.States.GOOD
            else:
                state = StudentAssignment.States.EXCELLENT
        return StudentAssignment.States.get_choice(state)

    @property
    def submission_is_received(self):
        """
        Submission is a first comment which student sent to the assignment
        marked as `online`.
        """
        return (self.first_student_comment_at is not None
                and self.assignment.is_online)

    @property
    def state_display(self):
        if self.score is not None:
            return "{0} ({1}/{2})".format(self.state.label,
                                          self.score,
                                          self.assignment.maximum_score)
        else:
            return self.state.label

    @property
    def state_short(self):
        if self.score is not None:
            return "{0}/{1}".format(self.score,
                                    self.assignment.maximum_score)
        else:
            return self.state.abbr

    @property
    def weight_score(self):
        return (self.score * self.assignment.weight) if self.score else None


def task_comment_attachment_upload_to(instance: "AssignmentComment", filename):
    sa = instance.student_assignment
    return f"{sa.assignment.files_root}/user_{sa.student_id}/{filename}"


class AssignmentComment(TimeStampedModel):
    student_assignment = models.ForeignKey(
        'StudentAssignment',
        verbose_name=_("AssignmentComment|student_assignment"),
        on_delete=models.CASCADE)
    text = models.TextField(
        _("AssignmentComment|text"),
        help_text=_("LaTeX+Markdown is enabled"),
        blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Author"),
        on_delete=models.CASCADE)
    attached_file = models.FileField(
        upload_to=task_comment_attachment_upload_to,
        max_length=150,
        blank=True)

    class Meta:
        ordering = ["created"]
        verbose_name = _("Assignment-comment")
        verbose_name_plural = _("Assignment-comments")

    def __str__(self):
        return ("Comment to {0} by {1}".format(
            smart_text(self.student_assignment.assignment),
            smart_text(self.student_assignment.student.get_full_name())))

    def get_city(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city()

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city_timezone()

    @property
    def city_aware_field_name(self):
        return self.__class__.student_assignment.field.name

    def created_local(self, tz=None):
        if not tz:
            tz = self.get_city_timezone()
        return timezone.localtime(self.created, timezone=tz)

    def get_update_url(self):
        return reverse('teaching:student_assignment_comment_edit', kwargs={
            "pk": self.student_assignment_id,
            "comment_pk": self.pk
        })

    @property
    def attached_file_name(self):
        return os.path.basename(self.attached_file.name)

    def attached_file_url(self):
        return reverse("study:assignment_attachments_download", kwargs={
            "sid": hashids.encode(learn_conf.ASSIGNMENT_COMMENT_ATTACHMENT,
                                  self.pk),
            "file_name": self.attached_file_name
        })

    def is_stale_for_edit(self):
        # Teacher can edit comment during 10 min period only
        return (now() - self.created).total_seconds() > 600


class AssignmentNotification(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("User"),
        on_delete=models.CASCADE)
    student_assignment = models.ForeignKey(
        'StudentAssignment',
        verbose_name=_("student_assignment"),
        on_delete=models.CASCADE)
    is_about_passed = models.BooleanField(_("About passed assignment"),
                                          default=False)
    is_about_creation = models.BooleanField(_("About created assignment"),
                                            default=False)
    is_about_deadline = models.BooleanField(_("About change of deadline"),
                                            default=False)
    is_unread = models.BooleanField(_("Unread"),
                                    default=True)
    is_notified = models.BooleanField(_("User is notified"),
                                      default=False)

    objects = models.Manager()
    unread = QueryManager(is_unread=True)

    class Meta:
        ordering = ["-created"]
        verbose_name = _("Assignment notification")
        verbose_name_plural = _("Assignment notifications")

    def clean(self):
        if self.is_about_passed and not self.user.is_teacher:
            raise ValidationError(_("Only teachers can receive notifications "
                                    "of passed assignments"))

    def __str__(self):
        return ("notification for {0} on {1}"
                .format(smart_text(self.user.get_full_name()),
                        smart_text(self.student_assignment)))

    def get_city(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city()

    def get_city_timezone(self):
        next_in_city_aware_mro = getattr(self, self.city_aware_field_name)
        return next_in_city_aware_mro.get_city_timezone()

    @property
    def city_aware_field_name(self):
        return self.__class__.student_assignment.field.name

    def created_local(self, tz=None):
        if not tz:
            tz = self.get_city_timezone()
        return timezone.localtime(self.created, timezone=tz)


class CourseNewsNotification(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("User"),
        on_delete=models.CASCADE)
    course_offering_news = models.ForeignKey(
        CourseNews,
        verbose_name=_("Course offering news"),
        on_delete=models.CASCADE)
    is_unread = models.BooleanField(_("Unread"),
                                    default=True)
    is_notified = models.BooleanField(_("User is notified"),
                                      default=False)

    objects = models.Manager()
    unread = QueryManager(is_unread=True)

    class Meta:
        ordering = ["-created"]
        verbose_name = _("Course offering news notification")
        verbose_name_plural = _("Course offering news notifications")

    def __str__(self):
        return ("notification for {0} on {1}"
                .format(smart_text(self.user.get_full_name()),
                        smart_text(self.course_offering_news)))


class Event(TimeStampedModel):
    objects = EventQuerySet.as_manager()
    venue = models.ForeignKey(
        Venue,
        verbose_name=_("CourseClass|Venue"),
        on_delete=models.PROTECT)
    name = models.CharField(_("CourseClass|Name"), max_length=255)
    description = models.TextField(
        _("Description"),
        blank=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    date = models.DateField(_("Date"))
    starts_at = models.TimeField(_("Starts at"))
    ends_at = models.TimeField(_("Ends at"))

    class Meta:
        ordering = ("-date", "-starts_at", "name")
        verbose_name = _("Non-course event")
        verbose_name_plural = _("Non-course events")

    def __str__(self):
        return "{}".format(smart_text(self.name))

    def clean(self):
        super().clean()
        # ends_at should be later than starts_at
        if self.starts_at >= self.ends_at:
            raise ValidationError(_("Event should end after it's start"))

    # this is needed to share code between CourseClasses and this model
    @property
    def type(self):
        return "noncourse"

    def get_absolute_url(self):
        return reverse('non_course_event_detail',
                       subdomain=settings.LMS_SUBDOMAIN,
                       args=[self.pk])


# FIXME: move -> cscenter app
class Useful(models.Model):
    question = models.CharField(_("Question"), max_length=255)
    answer = models.TextField(_("Answer"))
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)
    site = models.ForeignKey(Site, verbose_name=_("Site"),
                             default=settings.CENTER_SITE_ID,
                             on_delete=models.CASCADE)

    class Meta:
        ordering = ["sort"]
        verbose_name = _("Useful")
        verbose_name_plural = _("Useful")

    def __str__(self):
        return smart_text(self.question)
