from __future__ import unicode_literals

import time
import os.path
import datetime

import dateutil.parser as dparser

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.encoding import smart_text, python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext_lazy as _
from django.utils import timezone

from model_utils import Choices
from model_utils.fields import MonitorField, StatusField
from model_utils.models import TimeStampedModel

from . import utils

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
        help_text=(_("LaTeX+Markdown+HTML is enabled")))

    class Meta:
        ordering = ["name"]
        verbose_name = _("course")
        verbose_name_plural = _("courses")

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
        ordering = ["year", "type"]

    def __str__(self):
        return "{0} {1}".format(self.TYPES[self.type], self.year)

    @property
    def slug(self):
        return "{0}-{1}".format(self.year, self.type)

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
        help_text=_("LaTeX+Markdown+HTML is enabled; empty description will be replaced by course description"),
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

    # TODO: test this
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
    text = models.TextField(
        _("CourseNews|text"),
        help_text=(_("LaTeX+Markdown+HTML is enabled")))

    class Meta:
        ordering = ["-created"]
        verbose_name = _("Course news-singular")
        verbose_name_plural = _("Course news-plural")

    def __str__(self):
        return "{0} ({1})".format(smart_text(self.title),
                                  smart_text(self.course_offering))

@python_2_unicode_compatible
class Venue(models.Model):
    name = models.CharField(_("Name"), max_length=140)
    description = models.TextField(
        _("Description"),
        help_text=(_("LaTeX+Markdown is enabled")))

    class Meta:
        ordering = ["name"]
        verbose_name = _("Venue")
        verbose_name_plural = _("Venues")

    def __str__(self):
        return "{0}".format(smart_text(self.name))

    def get_absolute_url(self):
        return reverse('venue_detail', args=[self.pk])


@python_2_unicode_compatible
class CourseClass(TimeStampedModel):
    TYPES = Choices(('lecture', _("Lecture")),
                    ('seminar', _("Seminar")))

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
    name = models.CharField(_("Name"), max_length=140)
    description = models.TextField(
        _("Description"),
        blank=True,
        help_text=(_("LaTeX+Markdown+HTML is enabled")))
    materials = models.TextField(
        _("CourseClass|Materials"),
        blank=True,
        help_text=(_("LaTeX+Markdown+HTML is enabled")))
    date = models.DateField(_("Date"))
    starts_at = models.TimeField(_("Starts at"))
    ends_at = models.TimeField(_("Ends at"))

    class Meta:
        ordering = ["-date", "course_offering", "starts_at"]
        verbose_name = _("Class")
        verbose_name_plural = _("Classes")

    def __str__(self):
        return "{0}".format(smart_text(self.name))

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

    # TODO: test this
    @classmethod
    def by_semester(self, (year, season)):
        return self.objects.filter(
            course_offering__semester__type=season,
            course_offering__semester__year=year)


@python_2_unicode_compatible
class Assignment(TimeStampedModel):
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
    title = models.CharField(_("Asssignment|name"),
                             max_length=140)
    text = models.TextField(_("Assignment|text"),
                            help_text=_("LaTeX+Markdown+HTML is enabled"))
    attached_file = models.FileField(
        upload_to=(lambda instance, filename:
                       ("assignment_{0}/{1}/{2}"
                        .format(instance.pk,
                                # somewhat protecting against URL enumeration
                                int(time.time()) % 30,
                                filename))),
        blank=True)

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
    STATES = Choices(('not_checked', _("Assignment|not checked")),
                     # ('not_submitted', _("Assignment|not submitted")),
                     ('being_checked', _("Assignment|being checked")),
                     ('unsatisfactory', _("Assignment|unsatisfactory")),
                     ('pass', _("Assignment|pass")),
                     ('good', _("Assignment|good")),
                     ('excellent', _("Assignment|excellent")))

    assignment = models.ForeignKey(
        Assignment,
        verbose_name=_("AssignmentStudent|assignment"),
        on_delete=models.CASCADE)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("AssignmentStudent|student"),
        on_delete=models.CASCADE,
        limit_choices_to={'groups__name': 'Student'})
    state = StatusField(
        verbose_name=_("Asssignment|state"),
        choices_name='STATES',
        default='not_checked')
    state_changed = MonitorField(
        verbose_name=_("Asssignment|state changed"),
        monitor='state')

    class Meta:
        ordering = ["assignment", "student"]
        verbose_name = _("Assignment-student")
        verbose_name_plural = _("Assignment-students")

    def clean(self):
        if not self.student.is_student:
            raise ValidationError(_("Student field should point to "
                                    "an actual student"))

    def __str__(self):
        return "{0} - {1}".format(smart_text(self.assignment),
                                  smart_text(self.student.get_full_name))

    @property
    def status_display(self):
        return self.STATES[self.state]


@python_2_unicode_compatible
class AssignmentComment(TimeStampedModel):
    assignment_student = models.ForeignKey(
        AssignmentStudent,
        verbose_name=_("AssignmentComment|assignment_student"),
        on_delete=models.CASCADE)
    text = models.TextField(
        _("AssignmentComment|text"),
        help_text=_("LaTeX+Markdown is enabled"))
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Author"),
        on_delete=models.CASCADE)
    # TODO: test this
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
                                   .student.get_full_name)))

    @property
    def attached_file_name(self):
        return os.path.basename(self.attached_file.name)


class Enrollment(TimeStampedModel):
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Student"),
        on_delete=models.CASCADE)
    course_offering = models.ForeignKey(
        CourseOffering,
        verbose_name=_("Course offering"),
        on_delete=models.CASCADE)

    class Meta:
        ordering = ["student", "course_offering"]
        verbose_name = _("Enrollment")
        verbose_name_plural = _("Enrollments")

    def clean(self):
        if not self.student.is_student:
            raise ValidationError(_("Only students can enroll to courses"))

from . import signals
