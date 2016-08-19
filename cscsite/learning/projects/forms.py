from __future__ import absolute_import, unicode_literals

from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit, Hidden, \
    Button, Div, HTML, Fieldset
from django import forms
from django.utils.translation import ugettext_lazy as _

from core import comment_persistence
from core.forms import Ubereditor
from core.models import LATEX_MARKDOWN_ENABLED, LATEX_MARKDOWN_HTML_ENABLED
from learning.projects.models import ReportComment, Review


class ReportCommentForm(forms.ModelForm):
    prefix = "new_comment_form"

    text = forms.CharField(
        label=_("Add comment"),
        help_text=_(LATEX_MARKDOWN_ENABLED),
        required=False,
        widget=Ubereditor(attrs={'data-quicksend': 'true',
                                 'data-local-persist': 'true'}))
    attached_file = forms.FileField(
        label="",
        required=False,
        widget=forms.FileInput)

    def __init__(self, *args, **kwargs):
        report = kwargs.pop('report', None)
        author = kwargs.pop('author', None)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div('text'),
            Div(Div('attached_file',
                    Div(Submit('new_comment_form', _('Save')),
                        css_class='pull-right'),
                    css_class="form-inline"),
                css_class="form-group"))
        super(ReportCommentForm, self).__init__(*args, **kwargs)
        # Append required data not represented in form fields
        self.instance.report = report
        self.instance.author = author

    class Meta:
        model = ReportComment
        fields = ['text', 'attached_file']

    def clean(self):
        cleaned_data = super(ReportCommentForm, self).clean()
        if (not cleaned_data.get("text")
                and not cleaned_data.get("attached_file")):
            raise forms.ValidationError(
                _("Either text or file should be non-empty"))
        return cleaned_data

    def save(self, commit=True):
        comment = super(ReportCommentForm, self).save(commit)
        comment_persistence.report_saved(comment.text)
        return comment


class ReportReviewForm(forms.ModelForm):
    prefix = "review_form"

    class Meta:
        model = Review
        exclude = ("report", "reviewer")

    def __init__(self, *args, **kwargs):
        report = kwargs.pop('report', None)
        reviewer = kwargs.pop('author', None)
        super(ReportReviewForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(
            FormActions(
                Submit(self.prefix, _('Assess'))
            )
        )
        # Append required data not represented in form fields
        self.instance.report = report
        self.instance.reviewer = reviewer
