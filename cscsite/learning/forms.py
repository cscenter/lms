from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit, Hidden
from crispy_forms.bootstrap import FormActions
import floppyforms as forms

from learning.models import Course

class CourseUpdateForm(forms.ModelForm):
    name = forms.CharField(
        required=True,
        label=_("Course|name"),
        widget=forms.TextInput(attrs={'autofocus': 'autofocus'}))
    ongoing = forms.BooleanField(
        required=False,
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

class CourseOfferingEnrollForm(forms.Form):
    course_offering_pk = forms.IntegerField(required=True)
