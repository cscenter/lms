from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit, Hidden, Button, Div, HTML
from crispy_forms.bootstrap import FormActions
import floppyforms as forms

from learning.models import Course, CourseOffering, CourseOfferingNews, \
    CourseClass, Venue

class CourseUpdateForm(forms.ModelForm):
    name = forms.CharField(
        required=True,
        label=_("Course|name"),
        widget=forms.TextInput(attrs={'autofocus': 'autofocus'}))
    ongoing = forms.BooleanField(
        label=_("Course|ongoing"))

    def __init__(self, *args, **kwargs):
        super(CourseUpdateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-xs-2'
        self.helper.field_class = 'col-xs-7'
        self.helper.layout = Layout(
            'name',
            'ongoing',
            FormActions(Submit('submit', _("Submit"))))

    class Meta:
        model = Course
        fields = ['name', 'ongoing']


class CourseOfferingPKForm(forms.Form):
    course_offering_pk = forms.IntegerField(required=True)


class CourseOfferingEditDescrForm(forms.ModelForm):
    description = forms.CharField(
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
        required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'off',
                                      'autofocus': 'autofocus'}))
    text = forms.CharField(
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
        required=True,
        empty_label=None,
        widget=forms.Select(attrs={'autofocus': 'autofocus'}))
    venue = forms.ModelChoiceField(
        Venue.objects.all(),
        required=True,
        empty_label=None)
    type = forms.ChoiceField(
        required=True,
        choices=CourseClass.TYPES)
    name = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'autocomplete': 'off'}))
    description = forms.CharField(
        required=False,
        help_text=_("LaTeX+Markdown+HTML is enabled"),
        widget=forms.Textarea)
    materials = forms.CharField(
        required=False,
        help_text=_("LaTeX+Markdown+HTML is enabled"),
        widget=forms.Textarea)
    date = forms.DateField(required=True)
    starts_at = forms.TimeField(required=True)
    ends_at = forms.TimeField(required=True)

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
