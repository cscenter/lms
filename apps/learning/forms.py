import os
from typing import Optional

from crispy_forms.bootstrap import FormActions, StrictButton
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, BaseInput, Div, Field, Hidden, Layout, Submit

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from core.forms import ScoreField
from core.models import LATEX_MARKDOWN_ENABLED
from core.widgets import UbereditorWidget
from courses.constants import AssignmentStatuses
from courses.forms import AssignmentDurationField
from courses.models import Assignment
from grading.services import CheckerService
from learning.models import AssignmentSubmissionTypes, GraduateProfile, StudentAssignment

from .models import AssignmentComment


class SubmitLink(BaseInput):
    input_type = 'submit'

    def __init__(self, *args, **kwargs):
        self.field_classes = 'btn btn-link'
        super().__init__(*args, **kwargs)


class JesnyFileInput(forms.ClearableFileInput):
    template_name = 'widgets/file_input.html'


class AssignmentCommentForm(forms.ModelForm):
    prefix = "comment"

    text = forms.CharField(
        label=False,
        # help_text=_(LATEX_MARKDOWN_ENABLED),
        required=False,
        widget=UbereditorWidget(attrs={'data-quicksend': 'true',
                                       'data-local-persist': 'true',
                                       'data-helper-formatting': 'true'}))
    attached_file = forms.FileField(
        label="",
        required=False,
        widget=JesnyFileInput)

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
        if (not cleaned_data.get("text")
                and not cleaned_data.get("attached_file")):
            raise forms.ValidationError(
                _("Either text or file should be non-empty"))
        return cleaned_data


class AssignmentReviewForm(forms.Form):
    prefix = "review"

    text = forms.CharField(
        label=False,
        required=False,
        widget=UbereditorWidget(attrs={'data-quicksend': 'true',
                                       'data-local-persist': 'true',
                                       'data-helper-formatting': 'true'}))

    attached_file = forms.FileField(
        label="",
        required=False,
        widget=JesnyFileInput)

    score = ScoreField(required=False, label="")
    old_score = ScoreField(widget=forms.HiddenInput(), required=False)

    status = forms.ChoiceField(
        label="",
        required=False,
        choices=AssignmentStatuses.choices)
    old_status = forms.ChoiceField(
        widget=forms.HiddenInput(),
        required=False,
        choices=AssignmentStatuses.choices,
    )

    def __init__(self, student_assignment: StudentAssignment,
                       draft_comment: Optional[AssignmentComment] = None,
                       *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.student_assignment = student_assignment
        self.draft_comment = draft_comment
        score = student_assignment.score
        status = student_assignment.status
        if draft_comment is not None:
            self.draft_comment.type = AssignmentSubmissionTypes.COMMENT
            if draft_comment.meta:
                score = draft_comment.meta.get('score', score)
                status = draft_comment.meta.get('status', status)
        self.initial = {
            'text': '' if draft_comment is None else draft_comment.text,
            'score': score,
            'status': status,
            'old_score': student_assignment.score,
            'old_status': student_assignment.status
        }
        self.helper = FormHelper(self)
        maximum_score = student_assignment.assignment.maximum_score
        self.fields['score'].widget.attrs.update({'max': maximum_score})

    def clean(self):
        cleaned_data = super().clean()
        text = cleaned_data.get("text")
        file = cleaned_data.get("attached_file")
        score = cleaned_data.get('score')
        status = cleaned_data.get('status')
        old_score = cleaned_data.get('old_score')
        old_status = cleaned_data.get('old_status')
        if not (text or file) and (score, status) == (old_score, old_status):
            raise ValidationError(
                _("Nothing to send or update"), code='nothing_to_update')
        score = cleaned_data.get('score', None)
        maximum_score = self.student_assignment.assignment.maximum_score
        if score and score > maximum_score:
            msg = _("Score can't be larger than maximum one ({0})", )
            raise ValidationError(msg.format(maximum_score), code='too_high_score')
        if not self.student_assignment.is_status_transition_allowed(status):
            msg = f"Status {_(AssignmentStatuses(status).label)} is not allowed"
            raise ValidationError({"status": [msg]})
        return cleaned_data


# TODO: forbid save method
class AssignmentSolutionBaseForm(forms.ModelForm):
    """
    Base class for an assignment solution form.
    Dynamically adds `execution_time` field if asking time to completion
    is enabled in the course settings.
    """
    prefix = "solution"

    def __init__(self, assignment: Assignment, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['execution_time'] = AssignmentDurationField(
            label=_("Time Spent on Assignment"),
            required=assignment.course.ask_ttc,
            widget=forms.TextInput(attrs={'autocomplete': 'off',
                                          'class': 'form-control',
                                          'placeholder': _('hours:minutes')}),
            help_text=_("Requires the full format including minutes. "
                        "Do not include the time of previous submissions."))
        self.instance.type = AssignmentSubmissionTypes.SOLUTION
        self.helper = FormHelper(self)


class AssignmentSolutionDefaultForm(AssignmentSolutionBaseForm):
    text = forms.CharField(
        label=False,
        required=False,
        widget=UbereditorWidget(attrs={'data-quicksend': 'true',
                                       'data-local-persist': 'true',
                                       'data-helper-formatting': 'true'}))
    attached_file = forms.FileField(
        label="",
        required=False,
        widget=JesnyFileInput)

    class Meta:
        model = AssignmentComment
        fields = ('text', 'attached_file', 'execution_time')

    def __init__(self, assignment, *args, **kwargs):
        super().__init__(assignment, *args, **kwargs)
        self.helper.layout = Layout(
            Div('text', css_class='form-group-5'),
            Div('attached_file', css_class='form-group-5'),
            Div('execution_time'),
            FormActions(Submit('save', _('Send Solution'),
                               css_id=f'submit-id-{self.prefix}-save'),
                        css_class="form-group")
        )

    def clean(self):
        cleaned_data = super().clean()
        if (not cleaned_data.get("text")
                and not cleaned_data.get("attached_file")):
            raise forms.ValidationError(
                _("Either text or file should be non-empty"))
        return cleaned_data


def validate_attachment_has_file_extension(value):
    file_name = value.name
    if not file_name:
        raise ValidationError(_('File name is not provided'))
    file_name, ext = os.path.splitext(file_name)
    if not ext:
        raise ValidationError(
            _('`%(value)s` file name has no extension'),
            params={'value': file_name},
        )


class AssignmentSolutionYandexContestForm(AssignmentSolutionBaseForm):
    compiler = forms.ChoiceField(
        label=_("Compiler"),
    )
    attached_file = forms.FileField(
        label=_("Solution file"),
        required=True,
        validators=[validate_attachment_has_file_extension],
        widget=JesnyFileInput)

    class Meta:
        model = AssignmentComment
        fields = ('attached_file', 'execution_time')

    def __init__(self, assignment, *args, **kwargs):
        super().__init__(assignment, *args, **kwargs)
        checker = assignment.checker
        field_compiler = self.fields['compiler']
        field_compiler.choices = CheckerService.get_available_compiler_choices(checker)
        self.helper.layout = Layout(
            Div('compiler', css_class='form-group-5'),
            Div('attached_file', css_class='form-group-5'),
            Div('execution_time'),
            FormActions(Submit('save', _('Send Solution'),
                               css_id=f'submit-id-{self.prefix}-save'),
                        css_class="form-group")
        )

    def clean(self):
        cleaned_data = super().clean()
        invalid_attachment = 'attached_file' in self.errors
        if not cleaned_data.get("attached_file") and not invalid_attachment:
            raise forms.ValidationError(_("File should be non-empty"))
        return cleaned_data


class AssignmentModalCommentForm(forms.ModelForm):
    text = forms.CharField(
        label="",
        help_text=_(LATEX_MARKDOWN_ENABLED),
        required=False,
        widget=UbereditorWidget(attrs={'data-quicksend': 'true'}))

    class Meta:
        model = AssignmentComment
        fields = ['text']

    def __init__(self, *args, **kwargs):
        super(AssignmentModalCommentForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False

    def clean(self):
        cleaned_data = super(AssignmentModalCommentForm, self).clean()
        if not cleaned_data.get("text"):
            raise forms.ValidationError(_("Text should be non-empty"))
        return cleaned_data


class AssignmentScoreForm(forms.Form):
    score = ScoreField(required=False, label="")

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div(Hidden('grading_form', 'true'),
                Field('score', css_class='input-grade'),
                HTML("/" + str(kwargs.get('maximum_score'))),
                HTML("&nbsp;&nbsp;"),
                StrictButton('<i class="fa fa-floppy-o"></i>',
                             css_class="btn-primary",
                             type="submit"),
                css_class="form-inline"))
        if 'maximum_score' in kwargs:
            self.maximum_score = kwargs['maximum_score']
            self.helper['score'].update_attributes(max=self.maximum_score)
            del kwargs['maximum_score']
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        score = cleaned_data.get('score', None)
        if score and score > self.maximum_score:
            msg = _("Score can't be larger than maximum one ({0})")
            raise forms.ValidationError(msg.format(self.maximum_score))
        return cleaned_data


class TestimonialForm(forms.ModelForm):
    class Meta:
        model = GraduateProfile
        fields = ('testimonial',)
        widgets = {
            'testimonial': UbereditorWidget,
        }
        help_texts = {
            'testimonial': LATEX_MARKDOWN_ENABLED,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.disable_csrf = True

    def clean_testimonial(self):
        testimonial = self.cleaned_data['testimonial']
        return testimonial.strip()


class CourseEnrollmentForm(forms.Form):
    reason = forms.CharField(
        label=_("Почему вы выбрали этот курс?"),
        widget=forms.Textarea(),
        required=False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(Submit('enroll', 'Записаться на курс'))
