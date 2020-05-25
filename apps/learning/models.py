# -*- coding: utf-8 -*-

import logging
import os
import os.path
from secrets import token_urlsafe

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone
from django.utils.encoding import smart_text
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _
from djchoices import DjangoChoices, ChoiceItem
from model_utils.fields import MonitorField
from model_utils.managers import QueryManager
from model_utils.models import TimeStampedModel
from sorl.thumbnail import ImageField

from core.db.models import ScoreField, PrettyJSONField
from core.models import LATEX_MARKDOWN_HTML_ENABLED, Branch, Location, \
    SoftDeletionModel
from core.timezone import TimezoneAwareModel, now_local
from core.urls import reverse, branch_aware_reverse
from core.utils import hashids
from courses.models import Course, CourseNews, Assignment, StudentGroupTypes
from learning import settings as learn_conf
from learning.managers import EnrollmentDefaultManager, \
    EnrollmentActiveManager, EventQuerySet, StudentAssignmentManager, \
    GraduateProfileActiveManager, AssignmentCommentPublishedManager
from learning.settings import GradingSystems, GradeTypes
from users.constants import ThumbnailSizes
from users.models import StudentProfile
from users.thumbnails import UserThumbnailMixin, ThumbnailMixin, \
    get_thumbnail_or_stub, get_stub_factory

logger = logging.getLogger(__name__)


class StudentGroup(TimeStampedModel):
    type = models.CharField(
        verbose_name=_("Type"),
        max_length=100,
        choices=StudentGroupTypes.choices,
        default=StudentGroupTypes.BRANCH)
    name = models.CharField(
        verbose_name=_("Name"),
        max_length=255)
    course = models.ForeignKey(
        Course,
        verbose_name=_("Course offering"),
        related_name="student_groups",
        on_delete=models.CASCADE)
    meta = PrettyJSONField(
        verbose_name=_("Meta"),
        blank=True,
        null=True,
    )
    # Note: better to place in `meta`, but now we support only `branch` mode
    branch = models.ForeignKey(
        Branch,
        verbose_name=_("Branch"),
        related_name="+",  # Disable backwards relation
        on_delete=models.PROTECT,
        blank=True,
        null=True)
    enrollment_key = models.CharField(
        verbose_name=_("Enrollment key"),
        max_length=128)

    class Meta:
        verbose_name = _("Student Group")
        verbose_name_plural = _("Student Groups")

    def __str__(self):
        return self.name

    def save(self, **kwargs):
        created = self.pk is None
        if created and not self.enrollment_key:
            self.enrollment_key = token_urlsafe(18)  # 24 chars in base64
        super().save(**kwargs)


class AssignmentGroup(models.Model):
    assignment = models.ForeignKey(
        'courses.Assignment',
        verbose_name=_("Assignment"),
        on_delete=models.CASCADE)
    group = models.ForeignKey(
        StudentGroup,
        verbose_name=_("Group"),
        # Protect from deleting the last group of the assignment since it
        # will be interpreted as the assignment is available to all
        # student groups which is not true. Manually resolve this issue.
        on_delete=models.PROTECT)

    class Meta:
        verbose_name = _("Assignment Group")
        verbose_name_plural = _("Assignment Groups")
        constraints = [
            models.UniqueConstraint(fields=('assignment', 'group'),
                                    name='unique_assignment_group'),
        ]


class CourseClassGroup(models.Model):
    course_class = models.ForeignKey(
        'courses.CourseClass',
        verbose_name=_("Course Class"),
        on_delete=models.CASCADE)
    group = models.ForeignKey(
        StudentGroup,
        verbose_name=_("Group"),
        on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('course_class', 'group'),
                                    name='unique_class_student_group'),
        ]


class Enrollment(TimezoneAwareModel, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = 'course'

    GRADES = GradeTypes

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Student"),
        on_delete=models.CASCADE)
    student_profile = models.ForeignKey(
        StudentProfile,
        verbose_name=_("Student Profile"),
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
    student_group = models.ForeignKey(
        StudentGroup,
        verbose_name=_("Student Group"),
        related_name="enrollments",
        on_delete=models.PROTECT,
        blank=True,
        null=True)
    invitation = models.ForeignKey(
        'learning.Invitation',
        verbose_name=_("Invitation"),
        on_delete=models.PROTECT,
        null=True,
        blank=True)

    objects = EnrollmentDefaultManager()
    active = EnrollmentActiveManager()

    class Meta:
        unique_together = [('student', 'course')]
        verbose_name = _("Enrollment")
        verbose_name_plural = _("Enrollments")

    def __str__(self):
        return "{0} - {1}".format(smart_text(self.course),
                                  smart_text(self.student.get_full_name()))

    def save(self, *args, **kwargs):
        from learning.services import populate_assignments_for_student
        created = self.pk is None
        super().save(*args, **kwargs)
        if created or not self.is_deleted:
            populate_assignments_for_student(self)

    def clean(self):
        if self.student_profile_id and self.student_profile.user_id != self.student_id:
            raise ValidationError(_("Student profile does not match "
                                    "selected user"))

    def grade_changed_local(self, tz=None):
        if not tz:
            tz = self.get_timezone()
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


class CourseInvitation(models.Model):
    invitation = models.ForeignKey(
        'learning.Invitation',
        verbose_name=_("Course Invitation"),
        on_delete=models.CASCADE)
    course = models.ForeignKey(
        Course,
        verbose_name=_("Course offering"),
        on_delete=models.CASCADE)
    token = models.CharField(verbose_name=_("Token"), max_length=128)

    class Meta:
        verbose_name = _("Enrollment Invitation")
        verbose_name_plural = _("Enrollment Invitations")
        constraints = [
            models.UniqueConstraint(fields=('invitation', 'course'),
                                    name='unique_invitation_course'),
        ]

    def __str__(self):
        return f"[Invitation] course={self.course_id}"

    def clean(self):
        if (self.invitation_id and self.course_id and
                self.invitation.semester_id != self.course.semester_id):
            raise ValidationError(
                _('Course semester should match invitation semester'))

    def save(self, **kwargs):
        created = self.pk is None
        if created and not self.token:
            self.token = token_urlsafe(48)  # 64 chars in base64
        super().save(**kwargs)

    def get_absolute_url(self):
        return branch_aware_reverse(
            "course_enroll_by_invitation",
            kwargs={"course_token": self.token, **self.course.url_kwargs},
            subdomain=settings.LMS_SUBDOMAIN)

    def is_active(self):
        return self.course.enrollment_is_open


class Invitation(TimeStampedModel):
    name = models.CharField(_("Name"), max_length=255)
    token = models.CharField(verbose_name=_("Token"), max_length=128)
    semester = models.ForeignKey(
        "courses.Semester",
        verbose_name=_("Semester"),
        on_delete=models.CASCADE)
    branch = models.ForeignKey(
        Branch,
        verbose_name=_("Branch"),
        related_name="+",  # Disable backwards relation
        on_delete=models.PROTECT)
    courses = models.ManyToManyField(
        'courses.Course',
        through=CourseInvitation,
        verbose_name=_("Courses"))

    class Meta:
        verbose_name = _("Invitation")
        verbose_name_plural = _("Invitations")

    def __str__(self):
        return self.name

    @transaction.atomic
    def save(self, **kwargs):
        created = self.pk is None
        if created and not self.token:
            self.token = token_urlsafe(48)  # 64 chars in base64
        super().save(**kwargs)

    def get_absolute_url(self):
        return reverse("invitation:course_list",
                       kwargs={"token": self.token},
                       subdomain=settings.LMS_SUBDOMAIN)

    @property
    def is_active(self):
        today = now_local(self.branch.get_timezone()).date()
        start_at = self.semester.enrollment_start_at
        return start_at <= today <= self.semester.enrollment_end_at


class StudentAssignment(SoftDeletionModel, TimezoneAwareModel, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = 'assignment'

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
    execution_time = models.DurationField(
        verbose_name=_("Execution Time"),
        blank=True, null=True,
        help_text=_("The time spent by the student executing this task"),
    )
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
        has_perm = self.student.is_student or self.student.is_volunteer
        if not has_perm:
            raise ValidationError(_("Student field should point to "
                                    "an actual student"))
        if self.score and self.score > self.assignment.maximum_score:
            raise ValidationError(_("Grade can't be larger than maximum "
                                    "one ({0})")
                                  .format(self.assignment.maximum_score))

    def __str__(self):
        return "{0} - {1}".format(smart_text(self.assignment),
                                  smart_text(self.student.get_full_name()))

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
                   self.assignmentcomment_set(manager='published').all())

    @cached_property
    def state(self) -> ChoiceItem:
        score = self.score
        assignment = self.assignment
        passing_score = assignment.passing_score
        maximum_score = assignment.maximum_score
        satisfactory_range = maximum_score - passing_score
        if score is None:
            if not assignment.is_online or self.submission_is_received:
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
        return (self.assignment.weight * self.score) if self.score else None

    def get_execution_time_display(self):
        if self.execution_time is not None:
            total_minutes = int(self.execution_time.total_seconds()) // 60
            hours, minutes = divmod(total_minutes, 60)
            return str(_("{} hrs {:02d} min")).format(hours, minutes)


def task_comment_attachment_upload_to(instance: "AssignmentComment", filename):
    sa = instance.student_assignment
    return f"{sa.assignment.files_root}/user_{sa.student_id}/{filename}"


class AssignmentComment(SoftDeletionModel, TimezoneAwareModel, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = 'student_assignment'

    student_assignment = models.ForeignKey(
        'StudentAssignment',
        verbose_name=_("AssignmentComment|student_assignment"),
        on_delete=models.CASCADE)
    is_published = models.BooleanField(_("Published"), default=True)
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

    published = AssignmentCommentPublishedManager()

    class Meta:
        ordering = ["created"]
        verbose_name = _("Assignment-comment")
        verbose_name_plural = _("Assignment-comments")

    def __str__(self):
        return ("Comment to {0} by {1}".format(
            smart_text(self.student_assignment.assignment),
            smart_text(self.student_assignment.student.get_full_name())))

    def created_local(self, tz=None):
        if not tz:
            tz = self.get_timezone()
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_is_published = self.is_published

    def save(self, **kwargs):
        from learning.services import notify_new_assignment_comment
        created = self.pk is None
        is_published_before = getattr(self, '__original_is_published', False)
        super().save(**kwargs)
        # FIXME: remove notification logic from model
        # Send notifications only on publishing comment
        if self.is_published and (created or not is_published_before):
            notify_new_assignment_comment(self)
        self.__original_is_published = self.is_published


class AssignmentNotification(TimezoneAwareModel, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = 'student_assignment'

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

    def created_local(self, tz=None):
        if not tz:
            tz = self.get_timezone()
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
    branch = models.ForeignKey(
        Branch,
        verbose_name=_("Branch"),
        related_name="+",  # Disable backwards relation
        on_delete=models.CASCADE)
    venue = models.ForeignKey(
        Location,
        verbose_name=_("CourseClass|Venue"),
        null=True, blank=True,
        on_delete=models.PROTECT)
    name = models.CharField(_("CourseClass|Name"), max_length=255)
    description = models.TextField(
        _("Description"),
        blank=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    date = models.DateField(_("Date"))
    starts_at = models.TimeField(_("Starts at"))
    ends_at = models.TimeField(_("Ends at"))

    objects = EventQuerySet.as_manager()

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


class Useful(models.Model):
    question = models.CharField(_("Question"), max_length=255)
    answer = models.TextField(_("Answer"))
    sort = models.SmallIntegerField(_("Sort order"), blank=True, null=True)
    site = models.ForeignKey(Site, verbose_name=_("Site"),
                             default=settings.SITE_ID,
                             on_delete=models.CASCADE)

    class Meta:
        ordering = ["sort"]
        verbose_name = _("Useful")
        verbose_name_plural = _("Useful")

    def __str__(self):
        return smart_text(self.question)


def graduate_photo_upload_to(instance: "GraduateProfile", filename):
    _, ext = os.path.splitext(filename)
    filename = instance.student_profile.user.get_abbreviated_name_in_latin()
    return f"alumni/{instance.graduated_on.year}/{filename}{ext}"


class GraduateProfile(ThumbnailMixin, TimeStampedModel):
    TESTIMONIAL_CACHE_KEY = "csc_review"

    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Student"),
        on_delete=models.CASCADE,
        related_name="graduate_profile")
    student_profile = models.OneToOneField(
        StudentProfile,
        verbose_name=_("Student Profile"),
        on_delete=models.CASCADE,
        null=True, blank=True,
        related_name="graduate_profile")
    is_active = models.BooleanField(
        _("Activity"),
        default=True)
    graduated_on = models.DateField(
        verbose_name=_("Graduated on"),
        help_text=_("Graduation ceremony date"))
    academic_disciplines = models.ManyToManyField(
        'study_programs.AcademicDiscipline',
        verbose_name=_("Fields of study"),
        blank=True)
    graduation_year = models.PositiveSmallIntegerField(
        verbose_name=_("Graduation Year"),
        help_text=_("Helps filtering by year"),
        editable=False)
    photo = ImageField(
        _("Photo"),
        upload_to=graduate_photo_upload_to,
        blank=True)
    testimonial = models.TextField(
        _("Testimonial"),
        help_text=_("Testimonial about Computer Science Center"),
        blank=True)
    details = PrettyJSONField(
        verbose_name=_("Details"),
        blank=True,
    )

    objects = models.Manager()
    active = GraduateProfileActiveManager()

    class Meta:
        verbose_name = _("Graduate Profile")
        verbose_name_plural = _("Graduate Profiles")

    def __str__(self):
        return smart_text(self.student)

    def save(self, **kwargs):
        created = self.pk is None
        self.graduation_year = self.graduated_on.year
        if not self.details:
            self.details = {}
        super().save(**kwargs)

    def get_absolute_url(self):
        return reverse('student_profile', args=[self.student_profile.user_id],
                       subdomain=None)

    def get_thumbnail(self, geometry=ThumbnailSizes.BASE, **options):
        thumbnail_options = {
            "cropbox": None,
            **options
        }
        stub_factory = get_stub_factory(self.student_profile.user.gender,
                                        official=False)
        return get_thumbnail_or_stub(
            path_to_img=self.photo,
            geometry=geometry,
            stub_factory=stub_factory,
            **thumbnail_options)
