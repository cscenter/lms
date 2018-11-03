# -*- coding: utf-8 -*-

from distutils.util import strtobool

import django_filters
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, Row
from django.db.models import Case, Count, F, When, Value, Sum, IntegerField
from django.db.models import Q
from django.utils.timezone import now
from django.utils.translation import ugettext_lazy as _

from learning.projects.models import Project, ProjectStudent
from learning.settings import AcademicRoles, GradeTypes
from users.models import User

EMPTY_CHOICE = ('', _('Any'))
BOOLEAN_CHOICES = (
    ('', '---------'),
    ('false', 'Нет'),
    ('true', 'Да'),
)


class ProjectsFilter(django_filters.FilterSet):
    is_external = django_filters.TypedChoiceFilter(
        label=_("External project"),
        choices=BOOLEAN_CHOICES,
        coerce=strtobool
    )

    students = django_filters.ModelChoiceFilter(
        label=_("Student"),
        queryset=(User.objects
                  .filter(
                groups__in=[AcademicRoles.STUDENT_CENTER,
                            AcademicRoles.GRADUATE_CENTER])
                  .distinct()
                  .all())
    )

    supervisor = django_filters.CharFilter(lookup_expr='icontains',
                                           label=_("Supervisor"))

    # FIXME: do I really need to define this attribute?
    projectstudent__final_grade = django_filters.ChoiceFilter(
        choices=ProjectStudent._meta.get_field('final_grade').choices,
        lookup_expr='exact',
        label=_("Final grade"))

    class Meta:
        model = Project
        fields = ['semester', 'is_external', 'supervisor', 'students',
                  'projectstudent__final_grade']


    @property
    def form(self):
        if not hasattr(self, '_form'):
            today = now().date()
            self._form = super(ProjectsFilter, self).form
            self._form.helper = FormHelper(self._form)
            self._form.helper.disable_csrf = True
            self._form.helper.form_method = "GET"
            for attr in self.Meta.fields:
                self._form.fields[attr].help_text = ""
            self._form.helper.layout = Layout(
                Row(
                    Div('semester', css_class="col-xs-4"),
                    Div('is_external', css_class="col-xs-4"),
                    Div('supervisor', css_class="col-xs-4"),
                ),
                Row(
                    Div('students', css_class="col-xs-4"),
                    Div('projectstudent__final_grade', css_class="col-xs-4"),
                    Div(Submit('', _('Filter'), css_class="btn-block -inline-submit"),
                        css_class="col-xs-4")
                ),
            )
        return self._form


class SupervisorGradeFilter(django_filters.ChoiceFilter):
    NO = "no_any"
    NO_ALL = "no_all"
    YES = "yes_all"
    CHOICES = (
        (NO, "У кого-то нет"),
        (NO_ALL, "У всех нет"),
        (YES, "У всех есть"),
    )

    def __init__(self, *args, **kwargs):
        kwargs["choices"] = self.CHOICES
        super(SupervisorGradeFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value == self.NO:
            return qs.filter(projectstudent__supervisor_grade__isnull=True)
        elif value == self.YES or value == self.NO_ALL:
            qs = qs.annotate(without_grade_cnt=Sum(
                Case(
                    When(projectstudent__supervisor_grade__isnull=True,
                         then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField())))
            if value == self.YES:
                return qs.filter(without_grade_cnt=0)
            else:
                return (qs.annotate(ps_cnt=Count("projectstudent"))
                          .filter(without_grade_cnt=F('ps_cnt')))
        return qs


class PresentationGradeFilter(django_filters.ChoiceFilter):
    NO = "no_any"
    NO_ALL = "no_all"
    YES = "yes_all"
    CHOICES = (
        (NO, "У кого-то нет"),
        (NO_ALL, "У всех нет"),
        (YES, "У всех есть"),
    )

    def __init__(self, *args, **kwargs):
        kwargs["choices"] = self.CHOICES
        super(PresentationGradeFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value == self.NO:
            return qs.filter(projectstudent__presentation_grade__isnull=True)
        elif value == self.YES or value == self.NO_ALL:
            qs = qs.annotate(without_grade_cnt=Sum(
                Case(
                    When(projectstudent__presentation_grade__isnull=True,
                         then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField())))
            if value == self.YES:
                return qs.filter(without_grade_cnt=0)
            else:
                return (qs.annotate(ps_cnt=Count("projectstudent"))
                          .filter(without_grade_cnt=F('ps_cnt')))
        return qs


class SlidesStatusFilter(django_filters.ChoiceFilter):
    NO = "0"
    YES = "1"
    CHOICES = (
        (YES, "Есть"),
        (NO, "Нет"),
    )

    def __init__(self, *args, **kwargs):
        kwargs["choices"] = self.CHOICES
        super(SlidesStatusFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value == self.NO:
            return qs.filter(presentation="")
        elif value == self.YES:
            return qs.exclude(presentation="")
        return qs


class FinalGradeFilter(django_filters.ChoiceFilter):
    NO = "0"
    CHOICES = (
        (NO, "У кого-то нет"),
    )

    def __init__(self, *args, **kwargs):
        kwargs["choices"] = self.CHOICES
        super(FinalGradeFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        if value == self.NO:
            return qs.filter(
                projectstudent__final_grade=ProjectStudent.GRADES.not_graded)
        return qs


class ReportFilter(django_filters.ChoiceFilter):
    NO = "no_any"
    YES_ALL = "yes_all"
    CHOICES = (
        (NO, "Кто-то не прислал"),
        (YES_ALL, "Все прислали"),
    )

    def __init__(self, *args, **kwargs):
        kwargs["choices"] = self.CHOICES
        super(ReportFilter, self).__init__(*args, **kwargs)

    def filter(self, qs, value):
        # Exclude those who was graded, but didn't send a report.
        if value == self.NO:
            return (qs
                    .annotate(reports_cnt=Count("projectstudent__report"))

                    .annotate(ps_cnt=Sum(
                        Case(
                            When(Q(projectstudent__report__isnull=True) &
                                 ~Q(projectstudent__final_grade=GradeTypes.not_graded),
                                 then=Value(0)
                            ),
                            default=Value(1),
                            output_field=IntegerField()
                        )
                    ))
                    .exclude(reports_cnt=F("ps_cnt")))
        elif value == self.YES_ALL:
            qs = (qs.annotate(reports_cnt=Count("projectstudent__report"))
                    .annotate(ps_cnt=Sum(
                        Case(
                            When(Q(projectstudent__report__isnull=True) &
                                 ~Q(projectstudent__final_grade=GradeTypes.not_graded),
                                 then=Value(0)
                            ),
                            default=Value(1),
                            output_field=IntegerField()
                        )
                    ))
                    .filter(reports_cnt=F("ps_cnt")))
        return qs


class CurrentTermProjectsFilter(django_filters.FilterSet):

    participant_slides = SlidesStatusFilter(
        label=_("Participants presentation"), help_text="")
    supervisor_grade = SupervisorGradeFilter(label=_("Supervisor grade"),
                                             help_text="")
    presentation_grade = PresentationGradeFilter(label=_("Presentation grade"))
    final_grade = FinalGradeFilter(label=_("Final grade"), help_text="")
    report = ReportFilter(label=_("Report"), help_text="")

    class Meta:
        model = Project
        fields = [
            'supervisor_grade',
            'presentation_grade',
            'final_grade',
            'report',
            'participant_slides'
        ]

    @property
    def form(self):
        if not hasattr(self, '_form'):
            today = now().date()
            self._form = super(CurrentTermProjectsFilter, self).form
            self._form.helper = FormHelper(self._form)
            self._form.helper.disable_csrf = True
            self._form.helper.form_method = "GET"
            for attr in self.Meta.fields:
                self._form.fields[attr].help_text = ""
            self._form.helper.layout = Layout(
                Row(
                    Div('report', css_class="col-xs-4"),
                    Div('participant_slides', css_class="col-xs-4"),
                    Div('final_grade', css_class="col-xs-4"),
                ),
                Row(
                    Div('supervisor_grade', css_class="col-xs-4"),
                    Div('presentation_grade', css_class="col-xs-4"),
                    Div(Submit('', _('Filter'),
                               css_class="btn-block -inline-submit"),
                        css_class="col-xs-4")
                ),
            )
        return self._form
