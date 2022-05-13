from typing import List

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit, Row

from django import forms
from django.forms import SelectMultiple
from django.utils.translation import gettext_lazy as _

from core.widgets import JasnyFileInputWidget, UbereditorWidget
from courses.constants import AssignmentStatus, AssignmentFormat
from courses.models import Course
from learning.forms import SubmitLink
from learning.models import AssignmentComment, AssignmentSubmissionTypes


class AssignmentCommentForm(forms.ModelForm):
    prefix = "comment"

    text = forms.CharField(
        label=False,
        required=False,
        widget=UbereditorWidget(attrs={'data-quicksend': 'true',
                                       'data-local-persist': 'true',
                                       'data-helper-formatting': 'true'}))
    attached_file = forms.FileField(
        label="",
        required=False,
        widget=JasnyFileInputWidget)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.type = AssignmentSubmissionTypes.COMMENT
        if self.instance and self.instance.pk:
            draft_button_label = _('Update Draft')
        else:
            draft_button_label = _('Save Draft')
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Div('text', css_class='form-group-5'),
            Div('attached_file'),
            Div(Submit('save', _('Send Comment'),
                       css_id=f'submit-id-{self.prefix}-save'),
                SubmitLink('save-draft', draft_button_label,
                           css_id=f'submit-id-{self.prefix}-save-draft'),
                css_class="form-group"))

    class Meta:
        model = AssignmentComment
        fields = ('text', 'attached_file')

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("text") and not cleaned_data.get("attached_file"):
            raise forms.ValidationError(_("Either text or file should be non-empty"))
        return cleaned_data


class StudentAssignmentListFilter(forms.Form):

    format = forms.MultipleChoiceField(
        label=_("Assignment Format"),
        choices=AssignmentFormat.choices,
        required=False,
        widget=SelectMultiple(attrs={"size": 1, "class": "bs-select-hidden multiple-select"}),
    )

    status = forms.MultipleChoiceField(
        label=_("Status"),
        choices=filter(lambda c: c[0] != AssignmentStatus.NEW, AssignmentStatus.choices),
        initial=['new'],
        required=False,
        widget=SelectMultiple(attrs={"size": 1, "class": "bs-select-hidden multiple-select"}),
    )

    course = forms.TypedChoiceField(
        label=_("Course"),
        label_suffix='',
        coerce=int,
        empty_value=None,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"})
    )

    def __init__(self, enrolled_in: List[int], **kwargs):
        super().__init__(**kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Row(
                Div('format', css_class='col-xs-3'),
                Div('status', css_class='col-xs-3'),
                Div('course', css_class='col-xs-3'),
                Div(Submit('apply', _('Применить'),
                           css_class="btn btn-primary btn-outline "
                                     "btn-block -inline-submit"),
                    css_class="col-xs-3"),
            ))
        courses = (Course.objects.filter(pk__in=enrolled_in).select_related("meta_course"))
        self.fields['course'].choices = [
            (None, 'Все курсы'),
            *[(c.pk, c.name) for c in courses]
        ]
