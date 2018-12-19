# -*- coding: utf-8 -*-

import logging
import os.path
import time

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import smart_text
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, ChoiceItem
from model_utils.fields import MonitorField
from model_utils.managers import QueryManager
from model_utils.models import TimeStampedModel, TimeFramedModel
from sorl.thumbnail import ImageField

from core.db.models import ScoreField
from core.models import LATEX_MARKDOWN_HTML_ENABLED, City
from core.notifications import get_unread_notifications_cache
from core.utils import hashids
from courses.models import MetaCourse, Course, CourseTeacher, CourseNews, Venue, \
    CourseClass, Assignment
from learning import settings as learn_conf
from learning.managers import StudyProgramQuerySet, \
    EnrollmentDefaultManager, \
    EnrollmentActiveManager, NonCourseEventQuerySet, StudentAssignmentManager
from learning.settings import AssignmentStates, GradingSystems, \
    GradeTypes

logger = logging.getLogger(__name__)


class StudentAssignment(TimeStampedModel):
    class CommentAuthorTypes(DjangoChoices):
        NOBODY = ChoiceItem(0)
        STUDENT = ChoiceItem(1)
        TEACHER = ChoiceItem(2)

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
        return reverse('a_s_detail_teacher', kwargs={"pk": self.pk})

    def get_student_url(self):
        return reverse('a_s_detail_student', kwargs={"pk": self.pk})

    def has_unread(self):
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
                state = AssignmentStates.NOT_CHECKED
            else:
                state = AssignmentStates.NOT_SUBMITTED
        else:
            if score < passing_score or score == 0:
                state = AssignmentStates.UNSATISFACTORY
            elif score < passing_score + 0.4 * satisfactory_range:
                state = AssignmentStates.CREDIT
            elif score < passing_score + 0.8 * satisfactory_range:
                state = AssignmentStates.GOOD
            else:
                state = AssignmentStates.EXCELLENT
        return AssignmentStates.get_choice(state)

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

    @property
    def attached_file_name(self):
        return os.path.basename(self.attached_file.name)

    def attached_file_url(self):
        return reverse("assignment_attachments_download", kwargs={
            "sid": hashids.encode(learn_conf.ASSIGNMENT_COMMENT_ATTACHMENT,
                                  self.pk),
            "file_name": self.attached_file_name
        })

    def is_stale_for_edit(self):
        # Teacher can edit comment during 10 min period only
        return (now() - self.created).total_seconds() > 600


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
        ordering = ["student", "course"]
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


class NonCourseEvent(TimeStampedModel):
    objects = NonCourseEventQuerySet.as_manager()
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
        ordering = ["-date", "-starts_at", "name"]
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
        return reverse('non_course_event_detail', args=[self.pk])


class AreaOfStudy(models.Model):
    code = models.CharField(_("PK|Code"), max_length=2, primary_key=True)
    name = models.CharField(_("AreaOfStudy|Name"), max_length=255)
    description = models.TextField(
        _("AreaOfStudy|description"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Area of study")
        verbose_name_plural = _("Areas of study")

    def __str__(self):
        return smart_text(self.name)


# FIXME: move -> cscenter app
class StudyProgram(TimeStampedModel):
    year = models.PositiveSmallIntegerField(
        _("Year"), validators=[MinValueValidator(1990)])
    city = models.ForeignKey(City,
                             verbose_name=_("City"),
                             default=settings.DEFAULT_CITY_CODE,
                             on_delete=models.CASCADE)
    area = models.ForeignKey(AreaOfStudy, verbose_name=_("Area of Study"),
                             on_delete=models.CASCADE)
    description = models.TextField(
        _("StudyProgram|description"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED,
        blank=True, null=True)

    class Meta:
        verbose_name = _("Study Program")
        verbose_name_plural = _("Study Programs")

    objects = StudyProgramQuerySet.as_manager()


# FIXME: move -> cscenter app
class StudyProgramCourseGroup(models.Model):
    courses = models.ManyToManyField(
        MetaCourse,
        verbose_name=_("StudyProgramCourseGroup|courses"),
        help_text=_("Courses will be grouped with boolean OR"))
    study_program = models.ForeignKey(
        'StudyProgram',
        verbose_name=_("Study Program"),
        related_name='course_groups',
        on_delete=models.PROTECT)

    class Meta:
        verbose_name = _("Study Program Course")
        verbose_name_plural = _("Study Program Courses")


# TODO: rename to MoocCourse
# FIXME: move -> online_courses app?
class OnlineCourse(TimeStampedModel, TimeFramedModel):
    name = models.CharField(_("Course|name"), max_length=255)
    teachers = models.TextField(
        _("Online Course|teachers"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    description = models.TextField(
        _("Online Course|description"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    link = models.URLField(
        _("Online Course|Link"))
    photo = ImageField(
        _("Online Course|photo"),
        upload_to="online_courses/",
        blank=True)
    is_au_collaboration = models.BooleanField(
        _("Collaboration with AY"),
        default=False)
    is_self_paced = models.BooleanField(
        _("Without deadlines"),
        default=False)

    class Meta:
        db_table = 'online_courses'
        ordering = ["name"]
        verbose_name = _("Online course")
        verbose_name_plural = _("Online courses")

    def __str__(self):
        return smart_text(self.name)

    def is_ongoing(self):
        return self.start and self.start <= timezone.now()

    @property
    def avatar_url(self):
        if self.photo:
            return self.photo.url
        return None


# FIXME: move -> csclub app
class InternationalSchool(TimeStampedModel):
    name = models.CharField(_("InternationalSchool|name"), max_length=255)
    link = models.URLField(
        _("InternationalSchool|Link"))
    place = models.CharField(_("InternationalSchool|place"), max_length=255)
    deadline = models.DateField(_("InternationalSchool|Deadline"))
    starts_at = models.DateField(_("InternationalSchool|Start"))
    ends_at = models.DateField(_("InternationalSchool|End"), blank=True,
                               null=True)
    has_grants = models.BooleanField(
        _("InternationalSchool|Grants"),
        default=False)

    class Meta:
        db_table = 'international_schools'
        ordering = ["name"]
        verbose_name = _("International school")
        verbose_name_plural = _("International schools")

    def __str__(self):
        return smart_text(self.name)


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


# FIXME: move -> cscenter app
class InternshipCategory(models.Model):
    name = models.CharField(_("Category name"), max_length=255)
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)
    site = models.ForeignKey(Site, verbose_name=_("Site"),
                             default=settings.CENTER_SITE_ID,
                             on_delete=models.CASCADE)

    class Meta:
        ordering = ["sort"]
        verbose_name = _("Internship category")
        verbose_name_plural = _("Internship categories")

    def __str__(self):
        return smart_text(self.name)


# FIXME: move -> cscenter app
class Internship(TimeStampedModel):
    question = models.CharField(_("Question"), max_length=255)
    answer = models.TextField(_("Answer"))
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)
    category = models.ForeignKey(InternshipCategory,
                                 verbose_name=_("Internship category"),
                                 null=True,
                                 blank=True,
                                 on_delete=models.SET_NULL)

    class Meta:
        ordering = ["sort"]
        verbose_name = _("Internship")
        verbose_name_plural = _("Internships")

    def __str__(self):
        return smart_text(self.question)
