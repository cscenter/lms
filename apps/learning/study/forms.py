from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit

from django import forms
from django.utils.translation import gettext_lazy as _

from core.widgets import JasnyFileInputWidget, UbereditorWidget
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
