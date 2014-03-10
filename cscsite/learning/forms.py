from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit, Hidden
from crispy_forms.bootstrap import FormActions
import floppyforms as forms

from learning.models import Course, CourseOffering, CourseOfferingNews

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
