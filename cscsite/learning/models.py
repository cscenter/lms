# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

import datetime
import os.path
import posixpath
import time

import dateutil.parser as dparser
from annoying.fields import AutoOneToOneField
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.urlresolvers import reverse
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.encoding import smart_text, python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone
from model_utils import Choices, FieldTracker
from model_utils.fields import MonitorField, StatusField
from model_utils.managers import QueryManager
from model_utils.models import TimeStampedModel

from core.notifications import get_unread_notifications_cache
from learning import slides


LATEX_MARKDOWN_HTML_ENABLED = _(
    "LaTeX+"
    "<a href=\"http://en.wikipedia.org/wiki/Markdown\">Markdown</a>+"
    "HTML is enabled")
LATEX_MARKDOWN_ENABLED = _(
    "LaTeX+"
    "<a href=\"http://en.wikipedia.org/wiki/Markdown\">Markdown</a>"
    " is enabled")


@python_2_unicode_compatible
class Course(TimeStampedModel):
    name = models.CharField(_("Course|name"), max_length=140)
    slug = models.SlugField(
        _("News|slug"),
        max_length=70,
        help_text=_("Short dash-separated string "
                    "for human-readable URLs, as in "
                    "test.com/news/<b>some-news</b>/"),
        unique=True)
    description = models.TextField(
        _("Course|description"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED)

    class Meta:
        ordering = ["name"]
        verbose_name = _("Course")
        verbose_name_plural = _("Courses")

    def __str__(self):
        return smart_text(self.name)

    def get_absolute_url(self):
        return reverse('course_detail', args=[self.slug])


@python_2_unicode_compatible
class Semester(models.Model):
    TYPES = Choices(('spring', _("spring")),
                    ('autumn', _("autumn")))

    year = models.PositiveSmallIntegerField(
        _("CSCUser|Year"),
        validators=[MinValueValidator(1990)])
    type = StatusField(verbose_name=_("Semester|type"),
                       choices_name='TYPES')

    class Meta:
        ordering = ["-year", "type"]
        verbose_name = _("Semester")
        verbose_name_plural = _("Semesters")

    def __str__(self):
        return "{0} {1}".format(self.TYPES[self.type], self.year)

    @property
    def slug(self):
        return "{0}-{1}".format(self.year, self.type)

    @cached_property
    def starts_at(self):
        if self.type == 'spring':
            start_str = settings.SPRING_TERM_START
        else:
            start_str = settings.AUTUMN_TERM_START
        return (dparser
                .parse(start_str)
                .replace(tzinfo=timezone.utc,
                         year=self.year))

    @cached_property
    def ends_at(self):
        if self.type == 'spring':
            next_start_str = settings.AUTUMN_TERM_START
            next_year = self.year
        else:
            next_start_str = settings.SPRING_TERM_START
            next_year = self.year + 1
        return (dparser
                .parse(next_start_str)
                .replace(tzinfo=timezone.utc,
                         year=next_year)) - datetime.timedelta(days=1)


@python_2_unicode_compatible
class CourseOffering(TimeStampedModel):
    course = models.ForeignKey(
        Course,
        verbose_name=_("Course"),
        on_delete=models.PROTECT)
    teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Course|teachers"),
        related_name='teaching_set',
        limit_choices_to={'groups__name': 'Teacher'})
    semester = models.ForeignKey(
        Semester,
        verbose_name=_("Semester"),
        on_delete=models.PROTECT)
    description = models.TextField(
        _("Description"),
        help_text=_("LaTeX+Markdown+HTML is enabled; empty description "
                    "will be replaced by course description"),
        blank=True)
    enrolled_students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Enrolled students"),
        related_name='enrolled_on_set',
        blank=True,
        through='Enrollment')

    class Meta(object):
        ordering = ["-semester", "course__created"]
        verbose_name = _("Course offering")
        verbose_name_plural = _("Course offerings")

    def __str__(self):
        return "{0}, {1}".format(smart_text(self.course),
                                 smart_text(self.semester))

    def get_absolute_url(self):
        return reverse('course_offering_detail', args=[self.course.slug,
                                                       self.semester.slug])

    def has_unread(self):
        cache = get_unread_notifications_cache()
        return self in cache.courseoffering_news

    # FIXME(Dmitry): refactor this to use Semester object
    @classmethod
    def by_semester(cls, semester):
        (year, season) = semester
        return cls.objects.filter(semester__type=season,
                                  semester__year=year)

    @cached_property
    def is_ongoing(self):
        now = timezone.now()

        spring_term_start = (dparser
                             .parse(settings.SPRING_TERM_START)
                             .replace(tzinfo=timezone.utc))
        next_year = now + datetime.timedelta(days=365)
        # safer against leap years
        next_spring_term_start = (dparser
                                  .parse(settings.SPRING_TERM_START,
                                         default=next_year)
                                  .replace(tzinfo=timezone.utc))
        autumn_term_start = (dparser
                             .parse(settings.AUTUMN_TERM_START)
                             .replace(tzinfo=timezone.utc))

        if self.semester.year != now.year:
            return False
        if (self.semester.type == 'spring' and
                (now >= autumn_term_start or
                 now < spring_term_start)):
            return False
        if (self.semester.type == 'autumn' and
                (now < autumn_term_start or
                 now >= next_spring_term_start)):
            return False
        return True


@python_2_unicode_compatible
class CourseOfferingNews(TimeStampedModel):
    course_offering = models.ForeignKey(
        CourseOffering,
        verbose_name=_("Course offering"),
        on_delete=models.PROTECT)
    title = models.CharField(_("CourseNews|title"), max_length=140)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Author"),
        on_delete=models.PROTECT)
    text = models.TextField(
        _("CourseNews|text"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED)

    class Meta:
        ordering = ["-created"]
        verbose_name = _("Course news-singular")
        verbose_name_plural = _("Course news-plural")

    def __str__(self):
        return "{0} ({1})".format(smart_text(self.title),
                                  smart_text(self.course_offering))


@python_2_unicode_compatible
class Venue(models.Model):
    name = models.CharField(_("Venue|Name"), max_length=140)
    address = models.CharField(
        _("Venue|Address"),
        help_text=(_("Should be resolvable by Google Maps")),
        max_length=500,
        blank=True)
    description = models.TextField(
        _("Description"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    is_preferred = models.BooleanField(
        _("Preferred"),
        help_text=(_("Will be displayed on top of the venue list")),
        default=False)

    class Meta:
        ordering = ["-is_preferred", "name"]
        verbose_name = _("Venue")
        verbose_name_plural = _("Venues")

    def __str__(self):
        return "{0}".format(smart_text(self.name))

    def get_absolute_url(self):
        return reverse('venue_detail', args=[self.pk])


@python_2_unicode_compatible
class CourseClass(TimeStampedModel, object):
    TYPES = Choices(('lecture', _("Lecture")),
                    ('seminar', _("Seminar")))

    def _slides_file_name(self, filename):
        _, ext = os.path.splitext(filename)
        timestamp = self.date.strftime("%Y_%m_%d")
        course_offering = ("{0}_{1}"
                           .format(self.course_offering.course.slug,
                                   self.course_offering.semester.slug)
                           .replace("-", "_"))
        filename = ("{0}_{1}{2}"
                    .format(timestamp,
                            course_offering,
                            ext))
        return os.path.join('slides', course_offering, filename)

    course_offering = models.ForeignKey(
        CourseOffering,
        verbose_name=_("Course offering"),
        on_delete=models.PROTECT)
    venue = models.ForeignKey(
        Venue,
        verbose_name=_("CourseClass|Venue"),
        on_delete=models.PROTECT)
    type = StatusField(
        _("Type"),
        choices_name='TYPES')
    name = models.CharField(_("CourseClass|Name"), max_length=255)
    description = models.TextField(
        _("Description"),
        blank=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    slides = models.FileField(
        _("Slides"),
        blank=True,
        upload_to=_slides_file_name)
    video = models.TextField(
        _("CourseClass|Video"),
        blank=True,
        help_text=("{0}; {1}"
                   .format(LATEX_MARKDOWN_HTML_ENABLED,
                           _("please insert HTML for embedded video player"))))
    other_materials = models.TextField(
        _("CourseClass|Other materials"),
        blank=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED)
    date = models.DateField(_("Date"))
    starts_at = models.TimeField(_("Starts at"))
    ends_at = models.TimeField(_("Ends at"))

    class Meta:
        ordering = ["-date", "course_offering", "-starts_at"]
        verbose_name = _("Class")
        verbose_name_plural = _("Classes")

    def __str__(self):
        return smart_text(self.name)

    def get_absolute_url(self):
        return reverse('class_detail',
                       args=[self.course_offering.course.slug,
                             self.course_offering.semester.slug,
                             self.pk])

    def clean(self):
        super(CourseClass, self).clean()
        # ends_at should be later than starts_at
        if self.starts_at >= self.ends_at:
            raise ValidationError(_("Class should end after it's start"))

    # this is needed to properly set up fields for admin page
    def type_display_prop(self):
        return self.TYPES[self.type]
    type_display_prop.short_description = _("Type")
    type_display_prop.admin_order_field = 'type'
    type_display = property(type_display_prop)

    # FIXME(Dmitry): refactor this to use Semester object
    @classmethod
    def by_semester(cls, semester):
        (year, season) = semester
        return cls.objects.filter(
            course_offering__semester__type=season,
            course_offering__semester__year=year)

    @property
    def slides_file_name(self):
        return os.path.basename(self.slides.name)

    def upload_slides(self):
        course_offering = self.course_offering
        title = "{0}: {1}".format(course_offering, self)
        course = course_offering.course

        # a) SlideShare
        self.other_materials = slides.upload_to_slideshare(
            self.slides.file, title, self.description, tags=[course.slug])
        self.save()
        # b) Yandex.Disk
        yandex_path = posixpath.join(course.slug, self.slides_file_name)
        slides.upload_to_yandex(self.slides.file, yandex_path)


@receiver(post_save, sender=CourseClass)
def maybe_upload_slides(sender, instance, **kwargs):
    if instance.slides and not instance.other_materials:
        instance.upload_slides()


@python_2_unicode_compatible
class CourseClassAttachment(TimeStampedModel, object):
    course_class = models.ForeignKey(
        CourseClass,
        verbose_name=_("Class"),
        on_delete=models.CASCADE)
    material = models.FileField(upload_to="course_class_attachments")

    class Meta:
        ordering = ["course_class", "-created"]
        verbose_name = _("Class attachment")
        verbose_name_plural = _("Class attachments")

    def __str__(self):
        return "{0}".format(smart_text(self.material_file_name))

    @property
    def material_file_name(self):
        return os.path.basename(self.material.name)


@python_2_unicode_compatible
class Assignment(TimeStampedModel, object):
    course_offering = models.ForeignKey(
        CourseOffering,
        verbose_name=_("Course offering"),
        on_delete=models.PROTECT)
    assigned_to = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Assignment|assigned_to"),
        blank=True,
        through='AssignmentStudent')
    deadline_at = models.DateTimeField(_("Assignment|deadline"))
    is_online = models.BooleanField(_("Assignment|can be passed online"),
                                    default=True)
    # FIXME: rename this to "name"
    title = models.CharField(_("Asssignment|name"),
                             max_length=140)
    text = models.TextField(_("Assignment|text"),
                            help_text=LATEX_MARKDOWN_HTML_ENABLED)
    attached_file = models.FileField(
        upload_to=(lambda instance, filename:
                   ("assignments/{0}/{1}"
                    # somewhat protecting against URL enumeration
                    .format(int(time.time()) % 30,
                            filename))),
        blank=True)
    grade_min = models.PositiveSmallIntegerField(
        _("Assignment|grade_min"),
        default=2,
        validators=[MaxValueValidator(1000)])
    grade_max = models.PositiveSmallIntegerField(
        _("Assignment|grade_max"),
        default=5,
        validators=[MaxValueValidator(1000)])

    tracker = FieldTracker(fields=['deadline_at'])

    class Meta:
        ordering = ["created", "course_offering"]
        verbose_name = _("Assignment")
        verbose_name_plural = _("Assignments")

    def __init__(self, *args, **kwargs):
        super(Assignment, self).__init__(*args, **kwargs)
        if self.pk:
            self._original_course_offering_id = self.course_offering_id

    def clean(self):
        if (self.pk and
                self._original_course_offering_id != self.course_offering_id):
            raise ValidationError(_("Course offering modification "
                                    "is not allowed"))
        if self.grade_min > self.grade_max:
            raise ValidationError(_("Mininum grade should be lesser than "
                                    "(or equal to) maximum one"))

    def __str__(self):
        return "{0} ({1})".format(smart_text(self.title),
                                  smart_text(self.course_offering))

    @property
    def is_open(self):
        return self.deadline_at > timezone.now()

    @property
    def attached_file_name(self):
        return os.path.basename(self.attached_file.name)


@python_2_unicode_compatible
class AssignmentStudent(TimeStampedModel):
    STATES = Choices(('not_submitted', _("Assignment|not submitted")),
                     ('not_checked', _("Assignment|not checked")),
                     ('unsatisfactory', _("Assignment|unsatisfactory")),
                     ('pass', _("Assignment|pass")),
                     ('good', _("Assignment|good")),
                     ('excellent', _("Assignment|excellent")))
    SHORT_STATES = Choices(('not_submitted', "—"),
                           ('not_checked', "…"),
                           ('unsatisfactory', "2"),
                           ('pass', "3"),
                           ('good', "4"),
                           ('excellent', "5"))

    assignment = models.ForeignKey(
        Assignment,
        verbose_name=_("AssignmentStudent|assignment"),
        on_delete=models.CASCADE)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("AssignmentStudent|student"),
        on_delete=models.CASCADE,
        limit_choices_to={'groups__name': 'Student'})
    grade = models.PositiveSmallIntegerField(
        verbose_name=_("Grade"),
        null=True,
        blank=True)
    grade_changed = MonitorField(
        verbose_name=_("Assignment|grade changed"),
        monitor='grade')
    is_passed = models.BooleanField(
        verbose_name=_("Is passed"),
        help_text=_("It's online and has comments"),
        default=False)

    class Meta:
        ordering = ["assignment", "student"]
        verbose_name = _("Assignment-student")
        verbose_name_plural = _("Assignment-students")
        unique_together = [['assignment', 'student']]

    def clean(self):
        if not self.student.is_student:
            raise ValidationError(_("Student field should point to "
                                    "an actual student"))
        if self.grade > self.assignment.grade_max:
            raise ValidationError(_("Grade can't be larger than maximum "
                                    "one ({0})")
                                  .format(self.assignment.grade_max))

    def __str__(self):
        return "{0} - {1}".format(smart_text(self.assignment),
                                  smart_text(self.student.get_full_name()))

    def has_unread(self):
        cache = get_unread_notifications_cache()
        return self in cache.assignments

    @cached_property
    def state(self):
        grade_min = self.assignment.grade_min
        grade_max = self.assignment.grade_max
        grade_range = grade_max - grade_min
        if self.grade is None:
            if not self.assignment.is_online or self.is_passed:
                return 'not_checked'
            else:
                return 'not_submitted'
        else:
            if self.grade < grade_min:
                return 'unsatisfactory'
            elif self.grade < grade_min + 0.4 * grade_range:
                return 'pass'
            elif self.grade < grade_min + 0.8 * grade_range:
                return 'good'
            else:
                return 'excellent'

    @property
    def state_display(self):
        if self.grade is not None:
            return "{0} ({1}/{2})".format(self.STATES[self.state],
                                          self.grade,
                                          self.assignment.grade_max)
        else:
            return self.STATES[self.state]

    @property
    def state_short(self):
        if self.grade:
            return "{0}/{1}".format(self.grade,
                                    self.assignment.grade_max)
        else:
            return self.SHORT_STATES[self.state]


@python_2_unicode_compatible
class AssignmentComment(TimeStampedModel):
    assignment_student = models.ForeignKey(
        AssignmentStudent,
        verbose_name=_("AssignmentComment|assignment_student"),
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
        upload_to=(lambda instance, filename:
                   ("assignment_{0}/user_{1}/{2}/{3}"
                    .format(instance.assignment_student.assignment.pk,
                            instance.assignment_student.student.pk,
                            # somewhat protecting against URL enumeration
                            int(time.time()) % 30,
                            filename))),
        blank=True)

    class Meta:
        ordering = ["created"]
        verbose_name = _("Assignment-comment")
        verbose_name_plural = _("Assignment-comments")

    def __str__(self):
        return ("Comment to {0} by {1}"
                .format(smart_text(self.assignment_student
                                   .assignment),
                        smart_text(self.assignment_student
                                   .student.get_full_name())))

    @property
    def attached_file_name(self):
        return os.path.basename(self.attached_file.name)


@python_2_unicode_compatible
class Enrollment(TimeStampedModel):
    GRADES = Choices(('not_graded', _("Not graded")),
                     ('unsatisfactory', _("Enrollment|Unsatisfactory")),
                     ('pass', _("Enrollment|Pass")),
                     ('good', _("Good")),
                     ('excellent', _("Excellent")))
    SHORT_GRADES = Choices(('not_graded', "—"),
                           ('unsatisfactory', "н"),
                           ('pass', "з"),
                           ('good', "4"),
                           ('excellent', "5"))

    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Student"),
        on_delete=models.CASCADE)
    course_offering = models.ForeignKey(
        CourseOffering,
        verbose_name=_("Course offering"),
        on_delete=models.CASCADE)
    grade = StatusField(
        verbose_name=_("Enrollment|grade"),
        choices_name='GRADES',
        default='not_graded')
    grade_changed = MonitorField(
        verbose_name=_("Enrollment|grade changed"),
        monitor='grade')

    class Meta:
        ordering = ["student", "course_offering"]
        verbose_name = _("Enrollment")
        verbose_name_plural = _("Enrollments")

    def clean(self):
        if not self.student.is_student:
            raise ValidationError(_("Only students can enroll to courses"))

    def __str__(self):
        return "{0} - {1}".format(smart_text(self.course_offering),
                                  smart_text(self.student.get_full_name()))

    @property
    def grade_display(self):
        return self.GRADES[self.grade]

    @property
    def grade_short(self):
        return self.SHORT_GRADES[self.grade]


@python_2_unicode_compatible
class AssignmentNotification(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("User"),
        on_delete=models.CASCADE)
    assignment_student = models.ForeignKey(
        AssignmentStudent,
        verbose_name=_("assignment_student"),
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
                        smart_text(self.assignment_student)))


@python_2_unicode_compatible
class CourseOfferingNewsNotification(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("User"),
        on_delete=models.CASCADE)
    course_offering_news = models.ForeignKey(
        CourseOfferingNews,
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


@python_2_unicode_compatible
class NonCourseEvent(TimeStampedModel):
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
        return smart_text(self.name)

    def clean(self):
        super(NonCourseEvent, self).clean()
        # ends_at should be later than starts_at
        if self.starts_at >= self.ends_at:
            raise ValidationError(_("Event should end after it's start"))

    # this is needed to share code between CourseClasses and this model
    @property
    def type(self):
        return "noncourse"

    def get_absolute_url(self):
        return reverse('non_course_event_detail', args=[self.pk])


# XXX this is a gross hack of course. A better solution imo would be
# to put signal handlers right next to the models.
from .signals import *
