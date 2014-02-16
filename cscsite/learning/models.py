from __future__ import unicode_literals

import time

from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from model_utils import Choices
from model_utils.fields import MonitorField, StatusField
from model_utils.models import TimeStampedModel

from users.models import CSCUser

# TODO: check that teacher is a teacher
class Course(TimeStampedModel):
    name = models.CharField(_("Course|name"),
                            max_length=140)
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("Course|teacher"),
        null=True,
        on_delete=models.SET_NULL,
        limit_choices_to={'groups__name': 'Teacher'})
    ongoing = models.BooleanField(_("Course|ongoing"),
                                  default=True)

    class Meta(object):
        ordering = ["name", "created"]
        verbose_name = _("Course|course")
        verbose_name_plural = _("Course|courses")


class Assignment(TimeStampedModel):
    course = models.ForeignKey(Course,
                               verbose_name=_("Assignment|course"),
                               on_delete=models.CASCADE)
    deadline = models.DateField(_("Assignment|deadline"))
    online = models.BooleanField(_("Assignment|can be passed online"),
                                 default=True)
    title = models.CharField(_("Asssignment|name"),
                             max_length=140)
    text = models.TextField(_("Assignment|text"),
                            help_text=_("LaTeX+Markdown is enabled"))

    class Meta(object):
        ordering = ["course", "created"]
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
        on_delete=models.CASCADE)
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
