# -*- coding: utf-8 -*-
import datetime
import logging
import os
import os.path
from secrets import token_urlsafe

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Sum
from django.utils import timezone
from django.utils.encoding import smart_str
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from djchoices import DjangoChoices, ChoiceItem, C
from model_utils.fields import MonitorField
from model_utils.managers import QueryManager
from model_utils.models import TimeStampedModel
from sorl.thumbnail import ImageField

from core.db.fields import ScoreField, PrettyJSONField
from core.db.mixins import DerivableFieldsMixin
from core.models import LATEX_MARKDOWN_HTML_ENABLED, Branch, Location
from core.db.models import SoftDeletionModel
from core.timezone import TimezoneAwareMixin, now_local
from core.urls import reverse
from core.utils import hashids
from courses.models import Course, CourseNews, Assignment, StudentGroupTypes, \
    Semester, AssignmentSubmissionFormats
from files.models import ConfigurableStorageFileField
from files.storage import private_storage
from learning.managers import EnrollmentDefaultManager, \
    EnrollmentActiveManager, EventQuerySet, StudentAssignmentManager, \
    GraduateProfileActiveManager, AssignmentCommentPublishedManager, \
    GraduateProfileDefaultManager
from learning.settings import GradingSystems, GradeTypes, ENROLLMENT_DURATION
from learning.utils import humanize_duration
from users.constants import ThumbnailSizes
from users.models import StudentProfile
from users.thumbnails import ThumbnailMixin, \
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
        return self.name if self.branch_id is None else str(self.branch)

    def save(self, **kwargs):
        created = self.pk is None
        if created and not self.enrollment_key:
            self.enrollment_key = token_urlsafe(18)  # 24 chars in base64
        super().save(**kwargs)


class StudentGroupAssignee(models.Model):
    student_group = models.ForeignKey(
        StudentGroup,
        verbose_name=_("Student Group"),
        on_delete=models.CASCADE)
    assignee = models.ForeignKey(
        'courses.CourseTeacher',
        verbose_name=_("Assignee"),
        on_delete=models.CASCADE)
    assignment = models.ForeignKey(
        'courses.Assignment',
        verbose_name=_("Assignment"),
        blank=True, null=True,
        on_delete=models.CASCADE)

    class Meta:
        verbose_name = _("Student Group Assignee")
        verbose_name_plural = _("Student Group Assignees")
        constraints = [
            models.UniqueConstraint(
                # fields=('student_group', 'assignee', 'assignment'),
                fields=('student_group', 'assignee'),
                name='unique_assignee_per_student_or_assignment_group'
            ),
        ]

    def __str__(self):
        return "[StudentGroupAssignee] group: {} user: {} assignment: {}".format(
            self.student_group, self.assignee, self.assignment)


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


class EnrollmentPeriod(TimeStampedModel):
    site = models.ForeignKey(
        Site,
        verbose_name=_("Site"),
        on_delete=models.CASCADE)
    semester = models.ForeignKey(
        Semester,
        verbose_name=_("Semester"),
        on_delete=models.CASCADE)
    starts_on = models.DateField(
        _("Starts on"),
        blank=True,
        null=True,
        help_text=_("Leave blank to fill in with the date of the beginning "
                    "of the term"))
    ends_on = models.DateField(
        _("Closing Day"),
        blank=True,
        null=True,
        help_text=(_("Inclusive. Leave blank to calculate based on a default "
                     "duration ({} days)")).format(ENROLLMENT_DURATION))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('semester', 'site'),
                name='unique_enrollment_period_per_semester_per_site'),
        ]
        verbose_name = _("Enrollment Period")
        verbose_name_plural = _("Enrollment Periods")

    def __str__(self):
        return f"{self.semester} - {self.site}"

    def save(self, *args, **kwargs):
        term = self.semester
        if not self.starts_on:
            # Starts from the beginning of the term by default
            self.starts_on = term.starts_at.date()
        if not self.ends_on:
            duration = datetime.timedelta(days=ENROLLMENT_DURATION)
            self.ends_on = self.starts_on + duration
        super().save(*args, **kwargs)

    def clean(self):
        term_starts_on = self.semester.starts_at.date()
        term_ends_on = self.semester.ends_at.date()
        starts_on = self.starts_on or term_starts_on
        if not (term_starts_on <= starts_on <= term_ends_on):
            msg = _("Start of the enrollment period should be inside "
                    "term boundaries")
            raise ValidationError(msg)
        if self.ends_on:
            if starts_on > self.ends_on:
                if not self.starts_on:
                    msg = _("Deadline should be later than the expected "
                            "term start ({})").format(starts_on)
                else:
                    msg = _("Deadline should be later than the start of "
                            "the enrollment period")
                raise ValidationError(msg)

    def __contains__(self, date: datetime.date):
        return self.starts_on <= date <= self.ends_on


class Enrollment(TimezoneAwareMixin, TimeStampedModel):
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
        return "{0} - {1}".format(smart_str(self.course),
                                  smart_str(self.student.get_full_name()))

    def save(self, *args, **kwargs):
        created = self.pk is None
        super().save(*args, **kwargs)

    def clean(self):
        if self.student_profile_id and self.student_profile.user_id != self.student_id:
            raise ValidationError(_("Student profile does not match "
                                    "selected user"))
        if self.student_group_id and self.student_group.course_id != self.course_id:
            raise ValidationError(_("Student group must refer to one of the"
                                    "student groups of the selected course"))

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
        return reverse(
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

    @cached_property
    def is_active(self):
        today = now_local(self.branch.get_timezone()).date()
        return (EnrollmentPeriod.objects
                .filter(semester=self.semester,
                        site_id=settings.SITE_ID,
                        starts_on__lte=today,
                        ends_on__gte=today)
                .exists())


class AssignmentStatuses(DjangoChoices):
    # TODO: describe each status
    NEW = ChoiceItem('new', _("AssignmentStatus|New"))
    CHECK = ChoiceItem('check', _("AssignmentStatus|Check"))
    ACCEPTED = ChoiceItem('accept', _("AssignmentStatus|Accepted"))
    REWORK = ChoiceItem('rework', _("AssignmentStatus|Rework"))


class StudentAssignment(SoftDeletionModel, TimezoneAwareMixin, TimeStampedModel,
                        DerivableFieldsMixin):
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
    status = models.CharField(
        verbose_name=_("StudentAssignment|Status"),
        choices=AssignmentStatuses.choices,
        default=AssignmentStatuses.NEW,
        max_length=10)
    score = ScoreField(
        verbose_name=_("Grade"),
        null=True,
        blank=True)
    assignee = models.ForeignKey(
        'courses.CourseTeacher',
        verbose_name=_("Assignee"),
        on_delete=models.SET_NULL,
        blank=True, null=True,
        related_name="+",  # Disable backwards relation
    )
    trigger_auto_assign = models.BooleanField(
        null=True,
        help_text='Try to set assignee on first student activity',
        editable=False,
        default=True)
    watchers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Student Assignment Watchers"),
        related_name="+",  # Disable backwards relation
        blank=True,  # Make this field optional in django admin
    )
    score_changed = MonitorField(
        verbose_name=_("Assignment|grade changed"),
        monitor='score')
    execution_time = models.DurationField(
        verbose_name=_("Execution Time"),
        blank=True, null=True,
        editable=False,
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

    derivable_fields = [
        'execution_time',
        'first_student_comment_at',
        'last_comment_from',
    ]

    class Meta:
        ordering = ["assignment", "student"]
        verbose_name = _("Personal Assignment")
        verbose_name_plural = _("Personal Assignments")
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
        return "{0} - {1}".format(smart_str(self.assignment),
                                  smart_str(self.student.get_full_name()))

    def _compute_execution_time(self):
        time_spent = (AssignmentComment.objects
                      .filter(type=AssignmentSubmissionTypes.SOLUTION,
                              student_assignment=self)
                      .aggregate(total=Sum('execution_time')))
        execution_time = time_spent['total']  # Could be None
        if self.execution_time != execution_time:
            self.execution_time = execution_time
            return True
        return False

    def _compute_first_student_comment_at(self):
        first_student_submission = (AssignmentComment.objects
                                    .filter(student_assignment=self,
                                            author_id=self.student_id)
                                    .order_by('created')
                                    .values('created')
                                    .first())
        if not first_student_submission:
            return False
        first_student_submission_at = first_student_submission['created']
        if self.first_student_comment_at != first_student_submission_at:
            self.first_student_comment_at = first_student_submission_at
            return True
        return False

    def _compute_last_comment_from(self):
        latest_comment = (AssignmentComment.objects
                          .filter(student_assignment=self,
                                  type=AssignmentSubmissionTypes.COMMENT)
                          .order_by('-created')
                          .values('author_id')
                          .first())
        if not latest_comment:
            comment_from = self.CommentAuthorTypes.NOBODY
        elif latest_comment['author_id'] == self.student_id:
            comment_from = self.CommentAuthorTypes.STUDENT
        else:
            comment_from = self.CommentAuthorTypes.TEACHER
        if self.last_comment_from != comment_from:
            self.last_comment_from = comment_from
            return True
        return False

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
        return humanize_duration(self.execution_time)


def assignment_comment_attachment_upload_to(self: "AssignmentComment",
                                            filename) -> str:
    sa = self.student_assignment
    return "{}/assignments/{}/{}/user_{}/{}".format(
        sa.assignment.course.main_branch.site_id,
        sa.assignment.course.semester.slug,
        sa.assignment_id,
        sa.student_id,
        filename)


class AssignmentSubmissionTypes(DjangoChoices):
    COMMENT = C('comment', _("Comment"))
    SOLUTION = C('solution', _("Solution"))


class AssignmentComment(SoftDeletionModel, TimezoneAwareMixin, TimeStampedModel):
    TIMEZONE_AWARE_FIELD_NAME = 'student_assignment'

    student_assignment = models.ForeignKey(
        'StudentAssignment',
        verbose_name=_("AssignmentComment|student_assignment"),
        on_delete=models.CASCADE)
    type = models.CharField(
        verbose_name=_("AssignmentComment|Type"),
        max_length=42,
        choices=AssignmentSubmissionTypes.choices
    )
    execution_time = models.DurationField(
        verbose_name=_("Solution Execution Time"),
        blank=True, null=True,
        help_text=_("The time spent by the student executing this submission"))
    is_published = models.BooleanField(_("Published"), default=True)
    text = models.TextField(
        _("AssignmentComment|text"),
        help_text=_("LaTeX+Markdown is enabled"),
        blank=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Author"),
        on_delete=models.CASCADE)
    attached_file = ConfigurableStorageFileField(
        verbose_name=_("Attached File"),
        max_length=200,
        upload_to=assignment_comment_attachment_upload_to,
        storage=private_storage,
        blank=True)

    published = AssignmentCommentPublishedManager()

    class Meta:
        ordering = ["created"]
        verbose_name = _("Assignment-comment")
        verbose_name_plural = _("Assignment-comments")

    def __str__(self):
        return ("Comment to {0} by {1}".format(
            smart_str(self.student_assignment.assignment),
            smart_str(self.student_assignment.student.get_full_name())))

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        instance._loaded_is_published = instance.is_published
        return instance

    def save(self, **kwargs):
        from learning.services import update_student_assignment_derivable_fields, \
            trigger_auto_assign_for_student_assignment
        from learning.tasks import generate_notifications_about_new_submission
        created = self.pk is None
        is_published_before = getattr(self, '_loaded_is_published', False)
        super().save(**kwargs)
        has_been_published = self.is_published and (created or
                                                    not is_published_before)
        # Send notifications on publishing submission
        if has_been_published:
            trigger_auto_assign_for_student_assignment(self)
            # FIXME: move side effects outside model saving, e.g. to on_commit
            # TODO: replace with self.student_assignment.('first_student_comment_at', 'last_comment_from')
            update_student_assignment_derivable_fields(self)
            generate_notifications_about_new_submission.delay(
                assignment_submission_id=self.pk)
        self._loaded_is_published = self.is_published

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

    def get_attachment_download_url(self):
        return reverse("study:download_assignment_comment_attachment", kwargs={
            "sid": hashids.encode(self.pk),
            "file_name": self.attached_file_name
        })

    def is_stale_for_edit(self):
        # Teacher can edit comment during 10 min period only
        return (now() - self.created).total_seconds() > 600


def assignment_submission_attachment_upload_to(self: "SubmissionAttachment",
                                               filename) -> str:
    sa = self.submission.student_assignment
    return "{}/assignments/{}/{}/user_{}/{}".format(
        sa.assignment.course.main_branch.site_id,
        sa.assignment.course.semester.slug,
        sa.assignment_id,
        sa.student_id,
        filename)


class SubmissionAttachment(TimeStampedModel):
    """
    This model could be used for multiple attachments for assignment submission
    but currently stores only ipynb files converted to the html format.
    """
    submission = models.ForeignKey(
        AssignmentComment,
        verbose_name=_("Assignment Submission"),
        related_name='attachments',
        on_delete=models.CASCADE)
    attachment = ConfigurableStorageFileField(
        upload_to=assignment_submission_attachment_upload_to,
        storage=private_storage,
        max_length=200)

    class Meta:
        verbose_name = _("Assignment Submission Attachment")
        verbose_name_plural = _("Assignment Submission Attachments")

    def __str__(self):
        return self.file_name

    @property
    def file_name(self):
        return os.path.basename(self.attachment.name)

    @property
    def file_ext(self):
        _, ext = os.path.splitext(self.attachment.name)
        return ext

    def get_download_url(self):
        return reverse("study:download_submission_attachment", kwargs={
            "sid": hashids.encode(self.pk),
            "file_name": self.file_name
        })


class AssignmentNotification(TimezoneAwareMixin, TimeStampedModel):
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
                .format(smart_str(self.user.get_full_name()),
                        smart_str(self.student_assignment)))

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
                .format(smart_str(self.user.get_full_name()),
                        smart_str(self.course_offering_news)))


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
        return "{}".format(smart_str(self.name))

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


def graduate_photo_upload_to(instance: "GraduateProfile", filename):
    _, ext = os.path.splitext(filename)
    filename = instance.student_profile.user.get_abbreviated_name_in_latin()
    return f"alumni/{instance.graduated_on.year}/{filename}{ext}"


class GraduateProfile(ThumbnailMixin, TimeStampedModel):
    HISTORY_CACHE_KEY_PATTERN = "graduation_history_{site_id}"
    TESTIMONIAL_CACHE_KEY = "csc_review"
    STATS_CACHE_KEY_PATTERN = 'alumni_stats_{graduation_year}_{site_id}'

    student_profile = models.OneToOneField(
        StudentProfile,
        verbose_name=_("Student Profile"),
        on_delete=models.CASCADE,
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
        help_text=_("Academic disciplines that the student graduated from"),
        blank=True)
    graduation_year = models.PositiveSmallIntegerField(
        verbose_name=_("Graduation Year"),
        help_text=_("Helps filtering by year"),
        editable=False)
    photo = ImageField(
        _("Photo"),
        upload_to=graduate_photo_upload_to,
        max_length=200,
        blank=True)
    testimonial = models.TextField(
        _("Testimonial"),
        help_text=_("Testimonial about Computer Science Center"),
        blank=True)
    details = PrettyJSONField(
        verbose_name=_("Details"),
        blank=True,
    )
    diploma_number = models.CharField(
        verbose_name=_("Diploma Number"),
        max_length=64,
        blank=True
    )
    diploma_registration_number = models.CharField(
        verbose_name=_("Registration Number"),
        help_text=_("Registration number in the registry of education"),
        max_length=255,
        blank=True,
    )
    diploma_issued_on = models.DateField(
        verbose_name=_("Diploma Issued on"),
        blank=True, null=True
    )

    objects = GraduateProfileDefaultManager()
    active = GraduateProfileActiveManager()

    class Meta:
        verbose_name = _("Graduate Profile")
        verbose_name_plural = _("Graduate Profiles")

    def __str__(self):
        return smart_str(self.student_profile)

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
