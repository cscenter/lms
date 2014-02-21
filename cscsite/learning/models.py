from __future__ import unicode_literals

import time

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.core.urlresolvers import reverse
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices
from model_utils.fields import MonitorField, StatusField
from model_utils.models import TimeStampedModel

from users.models import CSCUser

# TODO: check that teacher is a teacher
class Course(TimeStampedModel):
    name = models.CharField(_("Course|name"), max_length=140)

    slug = models.SlugField(_("News|slug"),
                            max_length=70,
                            help_text=_("Short dash-separated string "
                                        "for human-readable URLs, as in "
                                        "test.com/news/<b>some-news</b>/"),
                            unique=True)

    description = models.TextField(
        _("Course|description"),
        max_length=(1024*4),
        help_text=(_("LaTeX+Markdown is enabled")))

    class Meta(object):
        ordering = ["name"]
        verbose_name = _("course")
        verbose_name_plural = _("courses")

    def __unicode__(self):
        return force_text(self.name)

    def get_absolute_url(self):
        return reverse('course_detail', args=[self.slug])

class Semester(models.Model):
    TYPES = Choices(('spring', _("spring")),
                    ('autumn', _("autumn")))

    year = models.PositiveSmallIntegerField(
        _("CSCUser|Year"),
        validators=[MinValueValidator(1990)])

    type = StatusField(verbose_name=_("Semester|type"),
                       choices_name='TYPES')

    class Meta(object):
        ordering = ["year", "type"]

    def __unicode__(self):
        return "{0} {1}".format(self.TYPES[self.type], self.year)

class CourseOffering(TimeStampedModel):
    course = models.ForeignKey(
        Course,
        verbose_name=_("Course"),
        on_delete=models.PROTECT)

    teachers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Course|teachers"),
        limit_choices_to={'groups__name': 'Teacher'})

    semester = models.ForeignKey(
        Semester,
        verbose_name=_("Semester"),
        on_delete=models.PROTECT)

    class Meta(object):
        ordering = ["-semester", "course__created"]
        verbose_name = _("Course offering")
        verbose_name_plural = _("Course offerings")

    def __unicode__(self):
        return "{0} ({1})".format(unicode(self.course),
                                  unicode(self.semester))

class CourseNews(TimeStampedModel):
    course_offering = models.ForeignKey(
        Course,
        verbose_name=_("Course offering"),
        on_delete=models.PROTECT)

    title = models.CharField(_("CourseNews|title"), max_length=140)

    text = models.TextField(_("CourseNews|text"),
                     max_length=(1024 * 4),
                     help_text=(_("LaTeX+Markdown is enabled")))

    class Meta(object):
        ordering = ["-created"]

class Assignment(TimeStampedModel):
    course_offering = models.ForeignKey(
        CourseOffering,
        verbose_name=_("Course"),
        on_delete=models.PROTECT)
    deadline = models.DateField(_("Assignment|deadline"))
    online = models.BooleanField(_("Assignment|can be passed online"),
                                 default=True)
    title = models.CharField(_("Asssignment|name"),
                             max_length=140)
    text = models.TextField(_("Assignment|text"),
                            help_text=_("LaTeX+Markdown is enabled"))

    class Meta(object):
        ordering = ["course_offering", "created"]
        verbose_name = _("Assignment|assignment")
        verbose_name_plural = _("Assignment|assignments")


# TODO: check if student is a student
class AssignmentStudent(TimeStampedModel):
    STATES = Choices(('not_checked', _("Assignment|not checked")),
                     ('being_checked', _("Assignment|being checked")),
                     ('unsatisfactory', _("Assignment|unsatisfactory")),
                     ('pass', _("Assignment|pass")),
                     ('good', _("Assignment|good")),
                     ('excellent', _("Assignment|excellent")))

    assignment = models.ForeignKey(
        Assignment,
        verbose_name=_("AssignmentStudent|assignment"),
        on_delete=models.PROTECT)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("AssignmentStudent|student"),
        on_delete=models.CASCADE,
        limit_choices_to={'groups__name': 'Student'})

    state = StatusField(verbose_name=_("Asssignment|state"),
                        choices_name='STATES')
    state_changed = MonitorField(verbose_name=_("Asssignment|state changed"),
                                 monitor='state')

    class Meta(object):
        ordering = ["assignment", "student"]
        verbose_name = _("Assignment|assignment")
        verbose_name_plural = _("Assignment|assignments")

    @property
    def status_display(self):
        return self.STATES[self.state]


class AssignmentComment(TimeStampedModel):
    assignment_student = models.ForeignKey(
        AssignmentStudent,
        verbose_name=_("AssignmentComment|assignment_student"),
        on_delete=models.CASCADE)
    text = models.TextField(
        _("AssignmentComment|text"),
        help_text=_("LaTeX+Markdown is enabled"))
    # TODO: test this
    file = models.FileField(
        upload_to=(lambda instance, filename:
                       "user_{0}/assignment_{1}/{2}_{3}".format(
                           instance.assignment_student.student.pk,
                           instance.assignment_student.assignment.pk,
                           time.time(),
                           filename)),
        blank=True)
