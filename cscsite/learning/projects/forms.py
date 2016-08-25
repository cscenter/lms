from __future__ import absolute_import, unicode_literals

from crispy_forms.bootstrap import FormActions, FieldWithButtons, StrictButton
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit, Hidden, \
    Button, Div, HTML, Fieldset, Row
from django import forms
from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.translation import ugettext_lazy as _

from core import comment_persistence
from core.forms import Ubereditor
from core.models import LATEX_MARKDOWN_ENABLED, LATEX_MARKDOWN_HTML_ENABLED
from learning.projects.models import ReportComment, Review, Report


class ReportForm(forms.ModelForm):
    prefix = "send_report_form"

    text = forms.CharField(
        label=_("Description"),
        help_text=_(LATEX_MARKDOWN_ENABLED),
        required=True,
        widget=Ubereditor(attrs={'data-quicksend': 'true',
                                 'data-local-persist': 'true'}))
    file = forms.FileField(
        label="",
        required=False,
        widget=forms.FileInput)

    class Meta:
        model = Report
        fields = ("text", "file")

    def __init__(self, *args, **kwargs):
        project_student = kwargs.pop('project_student', None)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div('text'),
            Div(Div('file',
                    Div(Submit('send_report_form', _('Send')),
                        css_class='pull-right'),
                    css_class="form-inline"),
                css_class="form-group"))
        super(ReportForm, self).__init__(*args, **kwargs)
        # Required data appended only on POST-action
        if project_student:
            self.instance.project_student = project_student

    # TODO: clean persisted comment. But it can be race condition. Or fuck it, students should be redirected from project page. Just wait 2 weeks before stale cache be cleaned?


class ReportStatusForm(forms.ModelForm):
    prefix = "report_status_change"

    class Meta:
        model = Report
        fields = ("status",)

    def __init__(self, *args, **kwargs):
        project_pk = kwargs.pop('project_pk', None)
        student_pk = kwargs.pop('student_pk', None)
        # TODO: log status change?
        super(ReportStatusForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_show_labels = False
        self.helper.form_action = reverse(
            "projects:project_report_update_status",
            kwargs={"project_pk": project_pk, "student_pk": student_pk}
        )
        self.helper.layout = Layout(
            FieldWithButtons("status", StrictButton(
                '<i class="fa fa-refresh" aria-hidden="true"></i>',
                name="new_comment_form",
                type="submit",
                css_class="btn btn-primary")),
        )

    def save(self, commit=True):
        instance = super(ReportStatusForm, self).save(commit)
        # TODO: send notification
        if "status" in self.changed_data:
            pass
        return instance


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


# TODO: throw warning if is_completed=True, but some marks not checked?
class ReportReviewForm(forms.ModelForm):
    prefix = "review_form"

    class Meta:
        model = Review
        # TODO: replace with __fields__
        fields = (
            "score_global_issue",
            "score_global_issue_note",
            "score_usefulness",
            "score_usefulness_note",
            "score_progress",
            "score_progress_note",
            "score_problems",
            "score_problems_note",
            "score_technologies",
            "score_technologies_note",
            "score_plans",
            "score_plans_note",
            "is_completed",
        )

        widgets = {
            "score_global_issue_note": forms.Textarea(attrs={"rows": 5}),
            "score_usefulness_note": forms.Textarea(attrs={"rows": 5}),
            "score_progress_note": forms.Textarea(attrs={"rows": 5}),
            "score_problems_note": forms.Textarea(attrs={"rows": 5}),
            "score_technologies_note": forms.Textarea(attrs={"rows": 5}),
            "score_plans_note": forms.Textarea(attrs={"rows": 5}),
        }

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


class ReportSummarizeForm(forms.ModelForm):
    prefix = "report_summary_form"

    class Meta:
        model = Report
        fields = (
            "score_activity",
            "score_quality",
            "final_score_note",
        )

    def __init__(self, *args, **kwargs):
        form_action = kwargs.pop('form_action', '')
        super(ReportSummarizeForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(
            FormActions(
                Submit(self.prefix, _('Send'))
            )
        )
        self.helper.form_action = reverse_lazy(
            "projects:project_report_summarize",
            kwargs={
                "project_pk": self.instance.project_student.project_id,
                "student_pk": self.instance.project_student.student_id
            }
        )
