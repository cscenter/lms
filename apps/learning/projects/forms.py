from crispy_forms.bootstrap import FormActions, FieldWithButtons, StrictButton
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div, HTML
from django import forms
from django.utils.translation import ugettext_lazy as _

from core import comment_persistence
from core.models import LATEX_MARKDOWN_ENABLED
from core.urls import reverse_lazy
from core.widgets import UbereditorWidget
from learning.projects.models import ReportComment, Review, Report, \
    ProjectStudent, PracticeCriteria


class StudentResultsModelForm(forms.ModelForm):
    class Meta:
        model = ProjectStudent
        fields = ('student',
                  # 'supervisor_grade',
                  # 'presentation_grade',
                  'final_grade')
        widgets = {
            "student": forms.HiddenInput(),
        }


class ReportForm(forms.ModelForm):
    prefix = "send_report_form"

    text = forms.CharField(
        label=_("Report content"),
        help_text=_(LATEX_MARKDOWN_ENABLED),
        required=True,
        widget=UbereditorWidget(attrs={'data-quicksend': 'true',
                                 'data-local-persist': 'true'}))
    file = forms.FileField(
        label="",
        required=False,
        widget=forms.FileInput)

    class Meta:
        model = Report
        fields = ("text", "file", "reporting_period")
        widgets = {
            "reporting_period": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        project_student = kwargs.pop('project_student', None)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'reporting_period',
            'text',
            Div(Div('file', css_class="form-inline"),
                css_class="form-group"),
            Div(Submit('send_report_form', "Отправить отчет")))
        super(ReportForm, self).__init__(*args, **kwargs)
        self.instance.project_student = project_student

    # TODO: clean persisted comment. But it can be race condition. Or fuck it, students should be redirected from project page. Just wait 2 weeks before stale cache be cleaned?


class ReportStatusForm(forms.ModelForm):
    prefix = "report_status_change"

    class Meta:
        model = Report
        fields = ("status",)

    def __init__(self, *args, **kwargs):
        # TODO: log status change? Can add to django log, only curators can change status
        super(ReportStatusForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_show_labels = False
        self.helper.form_action = self.instance.get_update_url()
        self.helper.layout = Layout(
            FieldWithButtons("status", StrictButton(
                '<i class="fa fa-floppy-o" aria-hidden="true"></i>',
                name="update_status_form",
                type="submit",
                css_class="btn btn-primary")),
        )

    def clean(self):
        cleaned_data = super(ReportStatusForm, self).clean()
        if (self.instance.score_activity is None or
                self.instance.score_quality is None):
            raise forms.ValidationError("Оценки куратора ещё не выставлены.")
        return cleaned_data


class ReportCommentForm(forms.ModelForm):
    prefix = "new_comment_form"

    text = forms.CharField(
        label=_("New comment"),
        help_text=_(LATEX_MARKDOWN_ENABLED),
        required=False,
        widget=UbereditorWidget(attrs={'data-local-persist': 'true'}))
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
                    Div(Submit('new_comment_form', _('Send')),
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
        fields = ("is_completed",)
        widgets = {
            "is_completed": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        report = kwargs.pop('report', None)
        reviewer = kwargs.pop('author', None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout.append(
            FormActions(
                HTML('<input type="hidden" name={} value=1>'.format(
                    self.prefix)),
                Submit(self.prefix + "-send", _('Complete assessment')),
                StrictButton(_("Save draft"),
                             name=self.prefix + "-draft",
                             type="submit",
                             css_class="btn-default"),
            )
        )
        # Append required data not represented in form fields
        self.instance.report = report
        self.instance.reviewer = reviewer

    def clean(self):
        cleaned_data = super().clean()
        if self.prefix + "-send" in self.data:
            cleaned_data["is_completed"] = True
        return cleaned_data


class PracticeCriteriaForm(forms.ModelForm):
    prefix = "review_practice_criteria"

    class Meta:
        model = PracticeCriteria
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
        )

        widgets = {
            "score_global_issue_note": forms.Textarea(attrs={"rows": 3}),
            "score_usefulness_note": forms.Textarea(attrs={"rows": 3}),
            "score_progress_note": forms.Textarea(attrs={"rows": 3}),
            "score_problems_note": forms.Textarea(attrs={"rows": 3}),
            "score_technologies_note": forms.Textarea(attrs={"rows": 3}),
            "score_plans_note": forms.Textarea(attrs={"rows": 3}),
            "is_completed": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.disable_csrf = True
        # Hide label text
        for field in self.Meta.fields:
            if field.endswith("_note"):
                self.fields[field].help_text = self.fields[field].label
                self.fields[field].label = ""


class ReportSummarizeForm(forms.ModelForm):
    prefix = "report_summary_form"

    complete = forms.BooleanField(required=False)

    class Meta:
        model = Report
        fields = (
            # "complete",
            "final_score_note",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Div('final_score_note'),
            FormActions(
                Submit(self.prefix + "-complete", _('Complete')),
                StrictButton(_("Save draft"),
                             name=self.prefix,
                             type="submit",
                             css_class="btn-default"),
            )
        )

        self.helper.form_action = reverse_lazy(
            "projects:project_report_summarize",
            kwargs={
                "project_pk": self.instance.project_student.project_id,
                "report_id": self.instance.id
            }
        )

    def save(self, commit=True):
        if self.cleaned_data.get('complete', False):
            self.instance.status = self._meta.model.COMPLETED
        instance = super().save(commit)
        return instance


class ReportCuratorAssessmentForm(forms.ModelForm):
    """Form shown to the curators to score report after it have been sent."""
    prefix = "report_curator_assessment_form"

    class Meta:
        model = Report
        fields = (
            "score_activity",
            "score_activity_note",
            "score_quality",
            "score_quality_note",
        )

        widgets = {
            "score_activity_note": forms.Textarea(attrs={"rows": 3}),
            "score_quality_note": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super(ReportCuratorAssessmentForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(
            FormActions(
                Submit(self.prefix, _('Save'))
            )
        )
        self.helper.form_action = reverse_lazy(
            "projects:project_report_curator_assessment",
            kwargs={
                "project_pk": self.instance.project_student.project_id,
                "report_id": self.instance.pk
            }
        )

        # Hide label text for notes
        for field in self.Meta.fields:
            if field.endswith("_note"):
                self.fields[field].help_text = self.fields[field].label
                self.fields[field].label = ""
