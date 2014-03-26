from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit, Hidden, Button, Div, HTML
from crispy_forms.bootstrap import FormActions
import floppyforms as forms

from learning.models import Course, CourseOffering, CourseOfferingNews, \
    CourseClass, Venue


class CourseOfferingPKForm(forms.Form):
    course_offering_pk = forms.IntegerField(required=True)


class CourseOfferingEditDescrForm(forms.ModelForm):
    description = forms.CharField(
        label=_("Description"),
        help_text=_("LaTeX+Markdown+HTML is enabled; empty description will be replaced by course description"),
        widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.add_input(Submit('save', _('Save'),
                                     css_class="pull-right"))
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
        help_text=_("LaTeX+Markdown+HTML is enabled"),
        required=True,
        widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.add_input(Submit('save', _('Save'),
                                     css_class="pull-right"))
        super(CourseOfferingNewsForm, self).__init__(*args, **kwargs)

    class Meta:
        model = CourseOfferingNews
        fields = ['title', 'text']


class CourseClassForm(forms.ModelForm):
    course_offering = forms.ModelChoiceField(
        CourseOffering.objects.all(),
        label=_("Course offering"),
        required=True,
        empty_label=None,
        widget=forms.Select(attrs={'autofocus': 'autofocus'}))
    venue = forms.ModelChoiceField(
        Venue.objects.all(),
        label=_("Venue"),
        required=True,
        empty_label=None)
    type = forms.ChoiceField(
        label=_("Type"),
        required=True,
        choices=CourseClass.TYPES)
    name = forms.CharField(
        label=_("Name"),
        required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'off'}))
    description = forms.CharField(
        label=_("Description"),
        required=False,
        help_text=_("LaTeX+Markdown+HTML is enabled"),
        widget=forms.Textarea)
    materials = forms.CharField(
        label=_("Materials"),
        required=False,
        help_text=_("LaTeX+Markdown+HTML is enabled"),
        widget=forms.Textarea)
    date = forms.DateField(
        required=True,
        label=_("Date"),
        help_text=_("Example: 1990-07-13"),
        widget=forms.DateInput(format="%Y-%m-%d"))
    starts_at = forms.TimeField(
        required=True,
        label=_("Starts at"),
        help_text=_("Example: 14:00"),
        widget=forms.TimeInput(format="%H:%M"))
    ends_at = forms.TimeField(
        required=True,
        label=_("Ends at"),
        help_text=_("Example: 14:40"),
        widget=forms.TimeInput(format="%H:%M"))

    def __init__(self, user, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div('course_offering',
                'venue',
                'type',
                'name',
                'description',
                'materials',
                css_class="form-group"),
            Div(Div('date',
                    HTML("&nbsp;"),
                    'starts_at',
                    HTML("&nbsp;"),
                    'ends_at',
                    css_class="form-inline"),
                css_class="form-group"),
            Div(
                Button('cancel', _('Cancel'),
                           onclick='history.go(-1);',
                           css_class="btn btn-default"),
                Submit('save', _('Save')),
                css_class="pull-right"))
        super(CourseClassForm, self).__init__(*args, **kwargs)

        self.fields['course_offering'].queryset = \
            CourseOffering.objects.all().filter(teachers=user)

    class Meta:
        model = CourseClass
        fields = '__all__'
