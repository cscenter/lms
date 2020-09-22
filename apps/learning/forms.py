from crispy_forms.bootstrap import StrictButton, InlineRadios, FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit, Hidden, \
    Div, HTML, BaseInput, Row
from django import forms
from django.utils.translation import gettext_lazy as _

from contests.constants import YandexCompilers
from contests.services import SubmissionService
from core.forms import GradeField
from core.models import LATEX_MARKDOWN_ENABLED
from core.timezone.constants import TIME_FORMAT_RU
from core.widgets import UbereditorWidget
from courses.forms import AssignmentDurationField
from learning.models import GraduateProfile, StudentAssignment, \
    AssignmentCommentTypes
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
        self.instance.type = AssignmentCommentTypes.COMMENT
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


class AssignmentSolutionBaseForm(forms.ModelForm):
    """
    Base class for an assignment solution form.
    Dynamically adds `execution_time` field if asking time to completion
    is enabled in the course settings.

    XXX:
        Make sure to include execution time field in the form layout if needed.
    """
    prefix = "solution"

    def __init__(self, course, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['execution_time'] = AssignmentDurationField(
            label=_("Time Spent on Assignment"),
            required=course.ask_ttc,
            widget=forms.TextInput(attrs={'autocomplete': 'off',
                                          'class': 'form-control',
                                          'placeholder': _('hours:minutes')}),
            help_text=_("Requires the full format including minutes. "
                        "Do not include the time of previous submissions."))
        self.instance.type = AssignmentCommentTypes.SOLUTION
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

    def __init__(self, course, *args, **kwargs):
        super().__init__(course, *args, **kwargs)
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


class AssignmentSolutionYandexContestForm(AssignmentSolutionBaseForm):
    compiler_id = forms.ChoiceField(
        label=_("Compiler"),
        choices=YandexCompilers.choices
    )
    attached_file = forms.FileField(
        label=_("Solution file"),
        required=False,
        widget=JesnyFileInput)

    class Meta:
        model = AssignmentComment
        fields = ('attached_file', 'execution_time')

    def __init__(self, course, *args, **kwargs):
        super().__init__(course, *args, **kwargs)
        self.helper.layout = Layout(
            Div('compiler_id', css_class='form-group-5'),
            Div('attached_file', css_class='form-group-5'),
            Div('execution_time'),
            FormActions(Submit('save', _('Send Solution'),
                               css_id=f'submit-id-{self.prefix}-save'),
                        css_class="form-group")
        )

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get("attached_file"):
            raise forms.ValidationError(
                _("File should be non-empty"))
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=commit)
        compiler_id = self.cleaned_data['compiler_id']
        SubmissionService.save_submission_settings(instance,
                                                   compiler_id=compiler_id)
        return instance


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
    score = GradeField(required=False, label="")

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