import datetime
from operator import attrgetter

from crispy_forms.bootstrap import TabHolder, Tab, PrependedText, FormActions, \
    StrictButton
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, HTML, Fieldset
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from core.forms import CANCEL_SAVE_PAIR
from core.models import LATEX_MARKDOWN_HTML_ENABLED, Branch
from core.timezone.forms import TimezoneAwareModelForm, \
    TimezoneAwareSplitDateTimeField
from core.timezone.constants import DATE_FORMAT_RU, TIME_FORMAT_RU
from core.widgets import UbereditorWidget, DateInputAsTextInput, \
    TimeInputAsTextInput, CityAwareSplitDateTimeWidget
from courses.constants import ClassTypes
from courses.models import Course, CourseNews, MetaCourse, CourseClass, \
    Assignment, LearningSpace, StudentGroupTypes

__all__ = ('CourseForm', 'CourseEditDescrForm', 'CourseNewsForm',
           'CourseClassForm', 'AssignmentForm')

from courses.utils import execution_time_string
from learning.models import StudentGroup

DROP_ATTACHMENT_LINK = '<a href="{}"><i class="fa fa-trash-o"></i>&nbsp;{}</a>'


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
        widget=DateInputAsTextInput(attrs={'class': 'datepicker',
                                           'autocomplete': 'off'}))
    starts_at = forms.TimeField(
        label=_("Starts at"),
        help_text=_("Format: hh:mm"),
        widget=TimeInputAsTextInput(format="%H:%M",
                                    attrs={'autocomplete': 'off'}))
    ends_at = forms.TimeField(
        label=_("Ends at"),
        help_text=_("Format: hh:mm"),
        widget=TimeInputAsTextInput(format="%H:%M",
                                    attrs={'autocomplete': 'off'}))

    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)
        assert course is not None
        super().__init__(*args, **kwargs)
        self.fields['venue'].queryset = self.fields['venue'].queryset.filter(
            branch_id=course.branch_id)
        self.fields['materials_visibility'].help_text = None
        self.fields['materials_visibility'].label = _("Visibility Setting")
        self.instance.course = course

        self.helper = FormHelper(self)
        if "instance" in kwargs:
            remove_links = "<ul class=\"list-unstyled __files\">{0}</ul>".format(
                "".join("<li>{}</li>".format(
                            DROP_ATTACHMENT_LINK.format(
                                attachment.get_delete_url(),
                                attachment.material_file_name))
                        for attachment
                        in kwargs["instance"].courseclassattachment_set.all()))
        else:
            remove_links = ""
        self.helper.layout = Layout(
            Div(Div('type', css_class='col-xs-2'),
                Div('venue', css_class='col-xs-3'),
                css_class='row'),
            Div('name',
                'description',
                css_class="form-group"),
            Div(Div(PrependedText('date', '<i class="fa fa-calendar"></i>'),
                    HTML("&nbsp;"),
                    PrependedText('starts_at', '<i class="fa fa-clock-o"></i>'),
                    HTML("&nbsp;"),
                    PrependedText('ends_at', '<i class="fa fa-clock-o"></i>'),
                    css_class="form-inline"),
                css_class="form-group"),
            Fieldset(_("Materials"),
                     Div(
                        Div('materials_visibility', css_class='col-xs-3'),
                        css_class='row'
                     ),
                     'slides',
                     'video_url',
                     Div('attachments', HTML(remove_links),),
                     'other_materials'),
            FormActions(
                StrictButton(_('<i class="fa fa-plus"></i> Save and add'),
                             name='_addanother', type="submit",
                             css_class="btn-primary btn-outline"),
                CANCEL_SAVE_PAIR
            )
        )

    class Meta:
        model = CourseClass
        fields = ['venue', 'type', 'materials_visibility', 'name',
                  'description', 'slides', 'attachments', 'video_url',
                  'other_materials', 'date', 'starts_at', 'ends_at']

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


def _get_label(student_group):
    if student_group.type == StudentGroupTypes.BRANCH:
        return f"{student_group.name} [{student_group.branch.site}]"
    return student_group.name


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
        widget=CityAwareSplitDateTimeWidget(date_format=DATE_FORMAT_RU,
                                            time_format=TIME_FORMAT_RU)
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
    restrict_to = forms.ModelMultipleChoiceField(
        label=_("Available for"),
        widget=forms.SelectMultiple(attrs={
            'class': 'multiple-select bs-select-hidden',
            'title': _('All groups'),
        }),
        required=False,
        help_text=_("Restrict assignment to selected groups. Available to all by default."),
        queryset=StudentGroup.objects.none())

    def __init__(self, *args, **kwargs):
        course = kwargs.pop('course', None)
        assert course is not None
        super().__init__(*args, **kwargs)
        self.instance.course = course
        qs = StudentGroup.objects.filter(course=course).order_by('pk')
        groups = list(qs)
        field_restrict_to = self.fields['restrict_to']
        # TODO: move to method
        field_restrict_to.queryset = qs
        if course.group_mode == StudentGroupTypes.BRANCH:
            field_restrict_to.label = _("Available to Branches")
            field_restrict_to.widget.attrs['title'] = _("All Branches")
            sites = set()
            for g in groups:
                # Special case when student group manually added in admin
                if g.branch_id:
                    g.branch = Branch.objects.get_by_pk(g.branch_id)
                    sites.add(g.branch.site_id)
            if len(sites) > 1:
                get_label = _get_label
            else:
                get_label = attrgetter('name')
        else:
            get_label = attrgetter('name')
        choices = [(sg.pk, get_label(sg)) for sg in groups]
        field_restrict_to.choices = choices

    class Meta:
        model = Assignment
        fields = ('title', 'text', 'deadline_at', 'attachments',
                  'submission_type', 'passing_score', 'maximum_score',
                  'weight', 'ttc', 'restrict_to')
