import datetime

from crispy_forms.bootstrap import TabHolder, Tab
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from core.forms import CANCEL_SAVE_PAIR
from core.models import LATEX_MARKDOWN_HTML_ENABLED
from core.timezone.constants import DATE_FORMAT_RU, TIME_FORMAT_RU
from core.timezone.forms import TimezoneAwareSplitDateTimeField, \
    TimezoneAwareModelForm
from core.widgets import UbereditorWidget, DateInputTextWidget, \
    TimeInputTextWidget
from courses.constants import ClassTypes
from courses.models import Course, CourseNews, MetaCourse, CourseClass, \
    Assignment, LearningSpace, StudentGroupTypes

__all__ = ('CourseForm', 'CourseEditDescrForm', 'CourseNewsForm',
           'CourseClassForm', 'AssignmentForm')

from courses.utils import execution_time_string
from learning.models import StudentGroup
from learning.services import StudentGroupService

DROP_ATTACHMENT_LINK = '<a href="{}"><i class="fa fa-trash-o"></i>&nbsp;{}</a>'


class MultipleStudentGroupField(forms.TypedMultipleChoiceField):
    def __init__(self, **kwargs):
        super().__init__(coerce=int, **kwargs)

    def prepare_value(self, value):
        if not value:
            return super().prepare_value(value)
        return [
            # Initial data stores model objects
            (sg.pk if isinstance(sg, StudentGroup) else sg) for sg in value
        ]

    def widget_attrs(self, widget):
        widget_attrs = super().widget_attrs(widget)
        widget_attrs.update({
            'class': 'multiple-select bs-select-hidden',
            'title': _('All groups'),
        })
        return widget_attrs


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
        widget=UbereditorWidget)

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
        model = MetaCourse
        fields = ('name_ru', 'name_en', 'description_ru', 'description_en')


class CourseEditDescrForm(forms.ModelForm):
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
                template='crispy_forms/square_tabs.html'
            ),
            CANCEL_SAVE_PAIR)
        super().__init__(*args, **kwargs)

    class Meta:
        model = Course
        fields = ['description_ru', 'description_en']
        widgets = {
            'description_ru': UbereditorWidget,
            'description_en': UbereditorWidget,
        }


class CourseNewsForm(forms.ModelForm):
    title = forms.CharField(
        label=_("Title"),
        required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'off',
                                      'autofocus': 'autofocus'}))
    text = forms.CharField(
        label=_("Text"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED,
        required=True,
        widget=UbereditorWidget)

    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div('title', 'text'),
            CANCEL_SAVE_PAIR)
        super().__init__(*args, **kwargs)
        if course:
            self.instance.course = course

    class Meta:
        model = CourseNews
        fields = ['title', 'text']


class CourseClassForm(forms.ModelForm):
    venue = forms.ModelChoiceField(
        queryset=LearningSpace.objects.select_related('location'),
        label=_("Venue"),
        empty_label=None)
    type = forms.ChoiceField(
        label=_("Type"),
        choices=ClassTypes.choices)
    name = forms.CharField(
        label=_("CourseClass|Name"),
        widget=forms.TextInput(attrs={'autocomplete': 'off'}))
    description = forms.CharField(
        label=_("Description"),
        required=False,
        help_text=LATEX_MARKDOWN_HTML_ENABLED,
        widget=UbereditorWidget(attrs={'autofocus': 'autofocus'}))
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
        label=_("CourseClass|Other materials"),
        required=False,
        help_text=LATEX_MARKDOWN_HTML_ENABLED,
        widget=UbereditorWidget)
    date = forms.DateField(
        label=_("Date"),
        help_text=_("Format: dd.mm.yyyy"),
        widget=DateInputTextWidget(attrs={'class': 'datepicker'}))
    starts_at = forms.TimeField(
        label=_("Starts at"),
        help_text=_("Format: hh:mm"),
        widget=TimeInputTextWidget())
    ends_at = forms.TimeField(
        label=_("Ends at"),
        help_text=_("Format: hh:mm"),
        widget=TimeInputTextWidget())
    restricted_to = MultipleStudentGroupField(
        label=_("Student Groups"),
        required=False,
        help_text=_("Restrict course class visibility in the student schedule"))

    class Meta:
        model = CourseClass
        fields = ['venue', 'type', 'date', 'starts_at', 'ends_at', 'name',
                  'description', 'slides', 'attachments', 'video_url',
                  'other_materials', 'materials_visibility', 'restricted_to']

    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)
        assert course is not None
        super().__init__(*args, **kwargs)
        self.fields['venue'].queryset = self.fields['venue'].queryset.filter(
            branch_id=course.main_branch_id)
        self.fields['materials_visibility'].help_text = _("Note that some materials would be available by direct link")
        field_restrict_to = self.fields['restricted_to']
        field_restrict_to.choices = StudentGroupService.get_choices(course)
        self.instance.course = course

    def clean_date(self):
        date = self.cleaned_data['date']
        # Validate this since 'course' could be invalid
        if 'course' in self.cleaned_data:
            course = self.cleaned_data['course']
            semester_start = course.semester.starts_at.date()
            semester_end = course.semester.ends_at.date()
            assert semester_start <= semester_end
            if not semester_start <= date <= semester_end:
                raise ValidationError(
                    _("Inconsistent with this course's "
                      "semester (from %(starts_at)s to %(ends_at)s)"),
                    code='date_out_of_semester',
                    params={'starts_at': semester_start,
                            'ends_at': semester_end})
        return date


class AssignmentDurationField(forms.DurationField):
    """
    Supports `hours:minutes` format instead of Django's '%d %H:%M:%S.%f'.
    """
    def prepare_value(self, value):
        if isinstance(value, datetime.timedelta):
            return execution_time_string(value)
        return value

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, datetime.timedelta):
            return value
        try:
            hours, minutes = map(int, str(value).split(":", maxsplit=1))
            value = datetime.timedelta(hours=hours, minutes=minutes)
        except ValueError:
            raise ValidationError(self.error_messages['invalid'], code='invalid')
        if value is None:
            raise ValidationError(self.error_messages['invalid'], code='invalid')
        return value


class AssignmentForm(TimezoneAwareModelForm):
    title = forms.CharField(
        label=_("Title"),
        widget=forms.TextInput(attrs={'autocomplete': 'off'}))
    text = forms.CharField(
        label=_("Text"),
        help_text=LATEX_MARKDOWN_HTML_ENABLED,
        widget=UbereditorWidget(attrs={'autofocus': 'autofocus'}))
    deadline_at = TimezoneAwareSplitDateTimeField(
        label=_("Deadline"),
        input_date_formats=[DATE_FORMAT_RU],
        input_time_formats=[TIME_FORMAT_RU],
    )
    attachments = forms.FileField(
        label=_("Attached files"),
        required=False,
        help_text=_("You can select multiple files"),
        widget=forms.ClearableFileInput(attrs={'multiple': 'multiple'}))
    passing_score = forms.IntegerField(
        label=_("Passing score"),
        initial=2)
    maximum_score = forms.IntegerField(
        label=_("Maximum score"),
        initial=5)
    weight = forms.DecimalField(
        label=_("Assignment Weight"),
        initial=1,
        min_value=0, max_value=1, max_digits=3, decimal_places=2,
        help_text=_("Assignment contribution to the course total score. "
                    "It takes into account in the gradebook.")
    )
    ttc = AssignmentDurationField(
        label=_("Time to Completion"),
        required=False,
        help_text=_("Estimated amount of time required for the task to be completed"),
        widget=forms.TextInput(
            attrs={"autocomplete": "off",
                   "class": "form-control",
                   "placeholder": _("hours:minutes")}))
    restricted_to = MultipleStudentGroupField(
        label=_("Available for"),
        required=False,
        help_text=_("Restrict assignment to selected groups. Available to all by default."))

    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)
        assert course is not None
        super().__init__(*args, **kwargs)
        self.instance.course = course
        field_restrict_to = self.fields['restricted_to']
        if course.group_mode == StudentGroupTypes.BRANCH:
            field_restrict_to.label = _("Available to Branches")
            field_restrict_to.widget.attrs['title'] = _("All Branches")
        field_restrict_to.choices = StudentGroupService.get_choices(course)

    class Meta:
        model = Assignment
        fields = ('title', 'text', 'deadline_at', 'attachments',
                  'submission_type', 'passing_score', 'maximum_score',
                  'weight', 'ttc', 'restricted_to')
