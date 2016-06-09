from __future__ import absolute_import, unicode_literals

from django.core.exceptions import ValidationError
from django.conf import settings
from django.utils.safestring import mark_safe
from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit, Hidden, \
    Button, Div, HTML, Fieldset
from crispy_forms.bootstrap import StrictButton, Tab, TabHolder, FormActions
import floppyforms.__future__ as forms
from modeltranslation.forms import TranslationModelForm

from core.forms import Ubereditor
from core.validators import FileValidator
from learning.settings import GRADES
from .models import Course, CourseOffering, CourseOfferingNews, \
    CourseClass, Venue, Assignment, AssignmentComment, StudentAssignment, \
    Enrollment, \
    LATEX_MARKDOWN_ENABLED, LATEX_MARKDOWN_HTML_ENABLED

CANCEL_BUTTON = Button('cancel', _('Cancel'),
                       onclick='history.go(-1);',
                       css_class="btn btn-default")
SUBMIT_BUTTON = Submit('save', _('Save'))
CANCEL_SAVE_PAIR = Div(CANCEL_BUTTON, SUBMIT_BUTTON, css_class="pull-right")


class CourseOfferingPKForm(forms.Form):
    course_offering_pk = forms.IntegerField(required=True)


class CourseOfferingEditDescrForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            TabHolder(
                Tab(
                    'RU',
                    'description_ru',
                ),
                Tab(
                    'EN',
                    'description_en',
                ),
            ),
            CANCEL_SAVE_PAIR)
        super(CourseOfferingEditDescrForm, self).__init__(*args, **kwargs)

        self.fields['description_ru'].required = True

    class Meta:
        model = CourseOffering
        fields = ['description_ru', 'description_en']
        widgets = {
            'description_ru': Ubereditor,
            'description_en': Ubereditor,
        }


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
    name_ru = forms.CharField(
        label=_("Course|name"),
        required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'off',
                                      'autofocus': 'autofocus'}))
    description_ru = forms.CharField(
        label=_("Course|description"),
        required=True,
        help_text=LATEX_MARKDOWN_HTML_ENABLED,
        widget=Ubereditor)


    @property
    def helper(self):
        helper = FormHelper()
        helper.layout = Layout(
            TabHolder(
                Tab(
                    'RU',
                    'name_ru',
                    'description_ru',
                ),
                Tab(
                    'EN',
                    'name_en',
                    'description_en',
                ),
            ),
            CANCEL_SAVE_PAIR)
        return helper

    class Meta:
        model = Course
        fields = ['name_ru', 'name_en', 'description_ru', 'description_en']


class CourseClassForm(forms.ModelForm):
    venue = forms.ModelChoiceField(
        Venue.objects.all(),
        label=_("Venue"),
        empty_label=None)
    type = forms.ChoiceField(
        label=_("Type"),
        choices=CourseClass.TYPES)
    name = forms.CharField(
        label=_("CourseClass|Name"),
        widget=forms.TextInput(attrs={'autocomplete': 'off'}))
    description = forms.CharField(
        label=_("Description"),
        required=False,
        help_text=LATEX_MARKDOWN_HTML_ENABLED,
        widget=Ubereditor(attrs={'autofocus': 'autofocus'}))
    slides = forms.FileField(
        label=_("Slides"),
        required=False,
        widget=forms.ClearableFileInput)
    attachments = forms.FileField(
        label=_("Attached files"),
        required=False,
        help_text=_("You can select multiple files"),
        widget=forms.ClearableFileInput(attrs={'multiple': 'multiple'}))
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

    def __init__(self, *args, **kwargs):
        remove_links = kwargs.get('remove_links', "")
        del kwargs['remove_links']
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(Div('type',
                        css_class='col-xs-2'),
                    Div('venue',
                        css_class='col-xs-3'),
                    css_class='row'),
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
                     Div(
                         Div('slides', css_class='col-xs-6'),
                         Div('attachments', HTML(remove_links),
                             css_class='col-xs-6'),
                         css_class='row'
                     ),
                     'video_url',
                     'other_materials'),
            FormActions(
                StrictButton(_('<i class="fa fa-plus"></i> Save and add'),
                             name='_addanother', type="submit",
                             css_class="btn-primary btn-outline"),
                CANCEL_SAVE_PAIR
            )
        )
        super(CourseClassForm, self).__init__(*args, **kwargs)

    class Meta:
        model = CourseClass
        fields = ['venue', 'type', 'name', 'description',
                  'slides', 'attachments', 'video_url', 'other_materials',
                  'date', 'starts_at', 'ends_at']

    def clean_date(self):
        date = self.cleaned_data['date']
        # this should be checked because 'course_offering' can be invalid
        if 'course_offering' in self.cleaned_data:
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
        required=False,
        widget=Ubereditor(attrs={'data-quicksend': 'true',
                                 'data-local-persist': 'true'}))
    attached_file = forms.FileField(
        label="",
        required=False,
        widget=forms.FileInput)

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_show_labels = False
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

    def clean(self):
        cleaned_data = super(AssignmentCommentForm, self).clean()
        if (not cleaned_data.get("text")
                and not cleaned_data.get("attached_file")):
            raise forms.ValidationError(
                _("Either text or file should be non-empty"))

        return cleaned_data


class AssignmentGradeForm(forms.Form):
    grade = forms.IntegerField(
        required=False,
        label="",
        min_value=0,
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
            self.grade_max = kwargs['grade_max']
            self.helper['grade'].update_attributes(max=self.grade_max)
            del kwargs['grade_max']
        super(AssignmentGradeForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(AssignmentGradeForm, self).clean()
        if cleaned_data['grade'] > self.grade_max:
            raise forms.ValidationError(_("Grade can't be larger than "
                                          "maximum one ({0})")
                                        .format(self.grade_max))
        return cleaned_data


class AssignmentForm(forms.ModelForm):
    title = forms.CharField(
        label=_("Title"),
        widget=forms.TextInput(attrs={'autocomplete': 'off'}))
    text = forms.CharField(
        label=_("Text"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED,
        widget=Ubereditor(attrs={'autofocus': 'autofocus'}))

    deadline_at = forms.SplitDateTimeField(
        label=_("Deadline"),
        input_date_formats=["%Y-%m-%d"],
        input_time_formats=["%H:%M"],
        widget = forms.SplitDateTimeWidget(date_format="%Y-%m-%d",
                                           time_format="%H:%M")
        # help_text=_("Example: 1990-07-13 12:00"),
        )
    attachments = forms.FileField(
        label=_("Attached file"),
        required=False,
        help_text=_("You can select multiple files"),
        widget=forms.ClearableFileInput(attrs={'multiple': 'multiple'}))
    is_online = forms.BooleanField(
        label=_("Can be passed online"),
        required=False)
    grade_min = forms.IntegerField(
        label=_("Assignment|grade_min"),
        initial=2)
    grade_max = forms.IntegerField(
        label=_("Assignment|grade_max"),
        initial=5)

    def __init__(self, *args, **kwargs):
        remove_links = kwargs.get('remove_links', "")
        del kwargs['remove_links']
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(
                'title',
                'text',
                Div(
                    Div('deadline_at', css_class='col-xs-6'),
                    Div('attachments', HTML(remove_links),
                        css_class='col-xs-6'),
                    css_class='row'
                ),
                Div(
                    Div('grade_min',
                        'grade_max',
                        css_class="form-inline"
                    ),
                    css_class="form-group"
                ),
                'is_online',
                css_class="form-group"
            ),
            CANCEL_SAVE_PAIR)
        super(AssignmentForm, self).__init__(*args, **kwargs)
        # No protection is needed if user is a superuser
        # if not user.is_superuser:
        #     self.fields['course_offering'].queryset = \
        #         CourseOffering.objects.filter(teachers=user)
        # else:
        #     self.fields['course_offering'].queryset = \
        #         CourseOffering.objects.all()

    class Meta:
        model = Assignment
        fields = ['title',
                  'text',
                  'deadline_at',
                  'attachments',
                  'is_online',
                  'grade_min',
                  'grade_max']


class MarksSheetTeacherImportGradesForm(forms.Form):
    """Import grades for particular CourseOffering from *.csv
    """

    def __init__(self, *args, **kwargs):
        c_slug = kwargs['c_slug']
        del(kwargs['c_slug'])
        super(MarksSheetTeacherImportGradesForm, self).__init__(*args, **kwargs)
        self.fields['assignment'].queryset = \
            Assignment.objects.filter(course_offering__course__slug=c_slug)

    assignment = forms.ModelChoiceField(
        queryset = Assignment.objects.all(),
        empty_label=None)

    csvfile = forms.FileField(
        label=_('Select csv file'),
        validators=[FileValidator(
            allowd_mimetypes=('text/csv', 'application/vnd.ms-excel')),
        ]
    )


class GradeBookFormFactory(object):

    GRADE_PREFIX = "a_s_{0}"
    FINAL_GRADE_PREFIX = "final_grade_{0}"

    @classmethod
    def build_form_class(cls, a_s_list, enrollment_list):
        """New form.Form subclass with StudentAssignment's list and Enrollment's grade

        Note:
            Django's widget with show_hidden_initial=True is rendered
            extremely slow. We get all initial values in  .get_form_class method,
            so it's unceccessary at all to use this feature.
        """
        fields = {cls.GRADE_PREFIX.format(a_s["pk"]):
                  forms.IntegerField(min_value=0,
                                     max_value=a_s["assignment__grade_max"],
                                     required=False)
                  for a_s in a_s_list if not a_s["assignment__is_online"]}
        fields.update({cls.FINAL_GRADE_PREFIX.format(e.pk):
                       forms.ChoiceField(GRADES) for e in enrollment_list})
        return type(str('MarksSheetTeacherForm'), (forms.Form,), fields)

    @classmethod
    def build_indexes(cls, student_assignments_list, enrollment_list):
        sas = student_assignments_list
        a_s_index = {cls.GRADE_PREFIX.format(a_s["pk"]): a_s for a_s in sas}
        enrollment_index = {cls.FINAL_GRADE_PREFIX.format(e.pk): e for e in
                            enrollment_list}
        return a_s_index, enrollment_index

    @classmethod
    def transform_to_initial(cls, a_s_list, enrollment_list):
        initial = {cls.GRADE_PREFIX.format(a_s["pk"]): a_s["grade"] for a_s in
                   a_s_list if not a_s["assignment__is_online"]}
        initial.update({cls.FINAL_GRADE_PREFIX.format(e.pk): e.grade for e in
                        enrollment_list})
        return initial
