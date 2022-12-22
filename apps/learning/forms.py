import os
from typing import Any, Dict, List, Optional

from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import BaseInput, Div, Layout, Submit

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from core.forms import ScoreField
from core.models import LATEX_MARKDOWN_ENABLED
from core.urls import reverse
from core.widgets import JasnyFileInputWidget, UbereditorWidget
from courses.constants import AssignmentStatus
from courses.forms import AssignmentDurationField
from courses.models import Assignment, CourseTeacher
from grading.services import CheckerService
from learning.models import (
    AssignmentSubmissionTypes, GraduateProfile, StudentAssignment, StudentGroupTeacherBucket, StudentGroup
)

from .models import AssignmentComment


class SubmitLink(BaseInput):
    input_type = 'submit'

    def __init__(self, *args, **kwargs):
        self.field_classes = 'btn btn-link'
        super().__init__(*args, **kwargs)


class DisableOptionSelectWidget(forms.Select):
    def __init__(self, *args, **kwargs):
        self._disabled_values = []
        super().__init__(*args, **kwargs)

    @property
    def disabled_options(self):
        return self._disabled_values

    @disabled_options.setter
    def disabled_options(self, value: List[Any]):
        self._disabled_values = value

    def create_option(self, name, value, *args, **kwargs) -> Dict[str, Any]:
        option_data = super().create_option(name, value, *args, **kwargs)
        if value in self.disabled_options:
            option_data['attrs']['disabled'] = 'disabled'
        return option_data


class AssignmentReviewForm(forms.Form):
    prefix = "review"

    text = forms.CharField(
        label=_("Comment"),
        required=False,
        widget=UbereditorWidget(attrs={'data-quicksend': 'true',
                                       'data-local-persist': 'true',
                                       'data-helper-formatting': 'true'}))

    attached_file = forms.FileField(
        label="",
        required=False,
        widget=JasnyFileInputWidget)

    score = ScoreField(required=False, label="")
    score_old = ScoreField(required=False, widget=forms.HiddenInput())

    status = forms.ChoiceField(
        label=_("Status"),
        required=True,
        widget=DisableOptionSelectWidget
    )
    status_old = forms.ChoiceField(
        widget=forms.HiddenInput(),
        required=True
    )

    def __init__(self, student_assignment: StudentAssignment,
                 draft_comment: Optional[AssignmentComment] = None,
                 **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.student_assignment = student_assignment
        text = ''
        score = student_assignment.score
        status = student_assignment.status
        if draft_comment is not None:
            assert draft_comment.type == AssignmentSubmissionTypes.COMMENT
            text = draft_comment.text
            if isinstance(draft_comment.meta, dict):
                score = draft_comment.meta.get('score', score)
                status = draft_comment.meta.get('status', status)
        self.initial = {
            'text': text,
            'score': score,
            'score_old': student_assignment.score,
            'status': status,
            'status_old': student_assignment.status
        }
        maximum_score = student_assignment.assignment.maximum_score
        self.fields['score'].validators.append(MaxValueValidator(limit_value=maximum_score))
        self.fields['score'].widget.attrs.update({'max': maximum_score})
        assignment_statuses = [(s.value, s.label)
                               for s in student_assignment.assignment.statuses]
        self.fields['status'].choices = assignment_statuses
        self.fields['status_old'].choices = assignment_statuses
        disabled_statuses = [status for status in AssignmentStatus.values
                             if not student_assignment.is_status_transition_allowed(status)]
        self.fields['status'].widget.disabled_options = disabled_statuses

    def clean(self):
        cleaned_data = super().clean()
        is_comment_added = cleaned_data.get("text") or cleaned_data.get("attached_file")
        # TODO: what if not all data are valid
        status = cleaned_data.get('status')
        status_old = cleaned_data.get('status_old')
        has_status_changed = status != status_old
        if not self.student_assignment.is_status_transition_allowed(status):
            raise ValidationError({"status": _("Please select a valid status")})
        score = cleaned_data.get('score', None)
        score_old = cleaned_data.get('score_old', None)
        has_score_changed = score != score_old
        if not (is_comment_added or has_status_changed or has_score_changed):
            raise ValidationError(_("Form is empty."), code='empty')
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
        widget=JasnyFileInputWidget)

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
        widget=JasnyFileInputWidget)

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


class StudentGroupTeacherBucketAdminForm(forms.ModelForm):

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)
        if instance:
            self.fields['groups'].queryset = StudentGroup.objects.filter(
                course_id=instance.assignment.course_id
            )
            self.fields['teachers'].queryset = CourseTeacher.objects.filter(
                course_id=instance.assignment.course_id
            )

    class Meta:
        model = StudentGroupTeacherBucket
        fields = ['groups', 'teachers', 'assignment']

    def clean_groups(self):
        selected_groups = self.cleaned_data['groups']
        assignment = self.instance.assignment
        bucket_pk = self.instance.pk
        buckets_with_same_groups = (StudentGroupTeacherBucket.objects
            .exclude(pk=bucket_pk)
            .filter(assignment=assignment,
                    groups__in=selected_groups)
        )
        if buckets_with_same_groups.exists():
            # It can be only one because of validation constraints
            bucket = buckets_with_same_groups.first()
            bucket_url = reverse('admin:learning_studentgroupteacherbucket_change', args=[bucket.pk])
            raise ValidationError(
                mark_safe(f"Выбранные студенческие группы пересекаться с "
                          f'<a href="{bucket_url}"><b>другим бакетом</b></a>.'
                          f'<br>Бакеты задания не должны пересекаться.'))
        return selected_groups
