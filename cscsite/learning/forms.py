from __future__ import absolute_import, unicode_literals

from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit, Hidden, \
    Button, Div, HTML, Fieldset
from crispy_forms.bootstrap import StrictButton
import floppyforms as forms

from core.forms import Ubereditor
from .models import Course, CourseOffering, CourseOfferingNews, \
    CourseClass, Venue, Assignment, AssignmentComment, AssignmentStudent, \
    Enrollment, OverallGrade, \
    LATEX_MARKDOWN_ENABLED, LATEX_MARKDOWN_HTML_ENABLED


CANCEL_SAVE_PAIR = Div(Button('cancel', _('Cancel'),
                              onclick='history.go(-1);',
                              css_class="btn btn-default"),
                       Submit('save', _('Save')),
                       css_class="pull-right")


class CourseOfferingPKForm(forms.Form):
    course_offering_pk = forms.IntegerField(required=True)


class CourseOfferingEditDescrForm(forms.ModelForm):
    description = forms.CharField(
        label=_("Description"),
        help_text="{0}; {1}".format(LATEX_MARKDOWN_HTML_ENABLED,
                                    _("empty description will be "
                                      "replaced by course description")),
        widget=Ubereditor)

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div('description'),
            CANCEL_SAVE_PAIR)
        super(CourseOfferingEditDescrForm, self).__init__(*args, **kwargs)

    class Meta:
        model = CourseOffering
        fields = ['description']


class CourseOfferingNewsForm(forms.ModelForm):
    title = forms.CharField(
        label=_("Title"),
        required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'off',
                                      'autofocus': 'autofocus'}))
    text = forms.CharField(
        label=_("Text"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED,
        required=True,
        widget=Ubereditor)

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div('title', 'text'),
            CANCEL_SAVE_PAIR)
        super(CourseOfferingNewsForm, self).__init__(*args, **kwargs)

    class Meta:
        model = CourseOfferingNews
        fields = ['title', 'text']


class CourseForm(forms.ModelForm):
    name = forms.CharField(
        label=_("Course|name"),
        required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'off',
                                      'autofocus': 'autofocus'}))
    description = forms.CharField(
        label=_("Course|description"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED,
        required=True,
        widget=Ubereditor)

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div('name', 'description'),
            CANCEL_SAVE_PAIR)
        super(CourseForm, self).__init__(*args, **kwargs)

    class Meta:
        model = Course
        fields = ['name', 'description']


class CourseClassForm(forms.ModelForm):
    course_offering = forms.ModelChoiceField(
        CourseOffering.objects.all(),
        label=_("Course offering"),
        empty_label=None,
        widget=forms.Select(attrs={'autofocus': 'autofocus'}))
    venue = forms.ModelChoiceField(
        Venue.objects.all(),
        label=_("Venue"),
        empty_label=None)
    type = forms.ChoiceField(
        label=_("Type"),
        choices=CourseClass.TYPES)
    name = forms.CharField(
        label=_("Name"),
        widget=forms.TextInput(attrs={'autocomplete': 'off'}))
    description = forms.CharField(
        label=_("Description"),
        required=False,
        help_text=LATEX_MARKDOWN_HTML_ENABLED,
        widget=Ubereditor)
    slides = forms.FileField(
        label=_("Slides"),
        required=False,
        widget=forms.ClearableFileInput)
    attachments = forms.FileField(
        label=_("Attached files"),
        required=False,
        help_text=_("You can select multiple files. New attachments "
                    "will replace old ones"),
        widget=forms.ClearableFileInput(attrs={'multiple': 'multiple'}))
    video = forms.CharField(
        label=_("CourseClass|Video"),
        required=False,
        help_text=("{0}; {1}"
                   .format(LATEX_MARKDOWN_HTML_ENABLED,
                           _("please insert HTML for embedded video player"))),
        widget=Ubereditor)
    other_materials = forms.CharField(
        label=_("Other materials"),
        required=False,
        help_text=LATEX_MARKDOWN_HTML_ENABLED,
        widget=Ubereditor)
    date = forms.DateField(
        label=_("Date"),
        # help_text=_("Example: 1990-07-13"),
        widget=forms.DateInput(format="%Y-%m-%d"))
    starts_at = forms.TimeField(
        label=_("Starts at"),
        # help_text=_("Example: 14:00"),
        widget=forms.TimeInput(format="%H:%M"))
    ends_at = forms.TimeField(
        label=_("Ends at"),
        # help_text=_("Example: 14:40"),
        widget=forms.TimeInput(format="%H:%M"))

    def __init__(self, user, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(Div(Div('course_offering',
                        css_class='col-xs-7'),
                    Div('type',
                        css_class='col-xs-2'),
                    Div('venue',
                        css_class='col-xs-3'),
                    css_class='row'),
                css_class='container inner'),
            Div('name',
                'description',
                css_class="form-group"),
            Div(Div('date',
                    HTML("&nbsp;"),
                    'starts_at',
                    HTML("&nbsp;"),
                    'ends_at',
                    css_class="form-inline"),
                css_class="form-group"),
            Fieldset(_("Materials"),
                     Div(Div(Div('slides',
                                 css_class='col-xs-6'),
                             Div('attachments',
                                 css_class='col-xs-6'),
                             css_class='row'),
                         css_class='container inner'),
                     'video',
                     'other_materials'),
            CANCEL_SAVE_PAIR)
        super(CourseClassForm, self).__init__(*args, **kwargs)

        # This is needed to guard against teachers adding classes to
        # other's courses. However, no protection is needed if user is
        # a superuser
        if not user.is_superuser:
            self.fields['course_offering'].queryset = \
                CourseOffering.objects.all().filter(teachers=user)

    class Meta:
        model = CourseClass
        fields = '__all__'

    def clean_date(self):
        date = self.cleaned_data['date']
        course_offering = self.cleaned_data['course_offering']
        semester_start = course_offering.semester.starts_at.date()
        semester_end = course_offering.semester.ends_at.date()
        assert semester_start <= semester_end
        if not semester_start <= date <= semester_end:
            raise ValidationError(
                _("Incosistent with this course's "
                  "semester (from %(starts_at)s to %(ends_at)s)"),
                code='date_out_of_semester',
                params={'starts_at': semester_start,
                        'ends_at': semester_end})
        return date


class AssignmentCommentForm(forms.ModelForm):
    text = forms.CharField(
        label=_("Text"),
        help_text=_(LATEX_MARKDOWN_ENABLED),
        widget=Ubereditor)
    attached_file = forms.FileField(
        label="",
        required=False,
        widget=forms.FileInput)

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div('text'),
            Div(Div('attached_file',
                    Div(Submit('save', _('Save')),
                        css_class='pull-right'),
                    css_class="form-inline"),
                css_class="form-group"))
        super(AssignmentCommentForm, self).__init__(*args, **kwargs)

    class Meta:
        model = AssignmentComment
        fields = ['text', 'attached_file']


class AssignmentGradeForm(forms.Form):
    grade = forms.IntegerField(
        required=False,
        label="",
        widget=forms.NumberInput(attrs={'min': 0, 'step': 1}))

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(Hidden('grading_form', 'true'),
                Field('grade', css_class='input-grade'),
                HTML("/" + str(kwargs.get('grade_max'))),
                HTML("&nbsp;&nbsp;"),
                StrictButton('<i class="fa fa-floppy-o"></i>',
                             css_class="btn-primary",
                             type="submit"),
                css_class="form-inline"))
        if 'grade_max' in kwargs:
            self.helper['grade'].update_attributes(max=kwargs['grade_max'])
            del kwargs['grade_max']
        super(AssignmentGradeForm, self).__init__(*args, **kwargs)


class AssignmentForm(forms.ModelForm):
    course_offering = forms.ModelChoiceField(
        CourseOffering.objects.all(),
        label=_("Course offering"),
        empty_label=None,
        widget=forms.Select(attrs={'autofocus': 'autofocus'}))
    title = forms.CharField(
        label=_("Title"),
        widget=forms.TextInput(attrs={'autocomplete': 'off'}))
    text = forms.CharField(
        label=_("Text"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED,
        widget=Ubereditor)

    deadline_at = forms.DateTimeField(
        label=_("Deadline"),
        # help_text=_("Example: 1990-07-13 12:00"),
        widget=forms.SplitDateTimeWidget(date_format="%Y-%m-%d",
                                         time_format="%H:%M"))
    attached_file = forms.FileField(
        label=_("Attached file"),
        required=False,
        widget=forms.FileInput)
    is_online = forms.BooleanField(
        label=_("Can be passed online"),
        required=False)
    grade_min = forms.IntegerField(
        label=_("Assignment|grade_min"),
        initial=2)
    grade_max = forms.IntegerField(
        label=_("Assignment|grade_max"),
        initial=5)

    def __init__(self, user, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div('course_offering',
                'title',
                'text',
                Div(Div('deadline_at',
                        'attached_file',
                        css_class="form-inline"),
                    css_class="form-group"),
                Div(Div('grade_min',
                        'grade_max',
                        css_class="form-inline"),
                    css_class="form-group"),
                'is_online',
                css_class="form-group"),
            CANCEL_SAVE_PAIR)
        super(AssignmentForm, self).__init__(*args, **kwargs)
        # No protection is needed if user is a superuser
        if not user.is_superuser:
            self.fields['course_offering'].queryset = \
                CourseOffering.objects.all().filter(teachers=user)

    class Meta:
        model = Assignment
        fields = ['course_offering',
                  'title',
                  'text',
                  'deadline_at',
                  'attached_file',
                  'is_online',
                  'grade_min',
                  'grade_max']


# Hipster factory class!
class MarksSheetTeacherFormFabrique(object):
    @staticmethod
    def build_form_class(a_s_list, enrollment_list):
        fields = {'a_s_{0}'.format(a_s.pk):
                  forms.ChoiceField(AssignmentStudent.SHORT_STATES,
                                    show_hidden_initial=True)
                  for a_s in a_s_list
                  if not a_s.assignment.is_online}
        fields.update({'final_grade_{0}_{1}'.format(e.course_offering.pk,
                                                    e.student.pk):
                       forms.ChoiceField(Enrollment.GRADES,
                                         show_hidden_initial=True)
                       for e in enrollment_list})
        return type(b'MarksSheetTeacherForm', (forms.Form,), fields)

    @staticmethod
    def build_indexes(a_s_list, enrollment_list):
        a_s_index = {'a_s_{0}'.format(a_s.pk): a_s
                     for a_s in a_s_list}
        enrollment_index = {'final_grade_{0}_{1}'.format(e.course_offering.pk,
                                                         e.student.pk): e
                            for e in enrollment_list}
        return a_s_index, enrollment_index

    @staticmethod
    def transform_to_initial(a_s_list, enrollment_list):
        initial = {'a_s_{0}'.format(a_s.pk): a_s.state
                   for a_s in a_s_list
                   if not a_s.assignment.is_online}
        initial.update({'final_grade_{0}_{1}'.format(e.course_offering.pk,
                                                     e.student.pk):
                        e.grade
                        for e in enrollment_list})
        return initial


class MarksSheetStaffFormFabrique(object):
    @staticmethod
    def build_form_class(students_list):
        fields = {'overall_{0}'.format(student.pk):
                  forms.ChoiceField(OverallGrade.GRADES,
                                    show_hidden_initial=True)
                  for student in students_list}
        return type(b'MarksSheetStaffForm', (forms.Form,), fields)

    @staticmethod
    def build_indexes(students_list):
        overalls_index = {'overall_{0}'.format(student.pk):
                          student.overall_grade
                          for student in students_list}
        return overalls_index

    @staticmethod
    def transform_to_initial(students_list):
        initial = {'overall_{0}'.format(student.pk):
                   student.overall_grade.grade
                   for student in students_list}
        return initial
