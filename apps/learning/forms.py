from crispy_forms.bootstrap import StrictButton
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit, Hidden, \
    Div, HTML, BaseInput, Row
from django import forms
from django.utils.translation import ugettext_lazy as _

from core.forms import GradeField
from core.models import LATEX_MARKDOWN_ENABLED
from core.widgets import UbereditorWidget
from learning.models import GraduateProfile
from .models import AssignmentComment


class SubmitLink(BaseInput):
    input_type = 'submit'

    def __init__(self, *args, **kwargs):
        self.field_classes = 'btn btn-link'
        super().__init__(*args, **kwargs)


class JesnyFileInput(forms.ClearableFileInput):
    template_name = 'widgets/file_input.html'


class AssignmentCommentForm(forms.ModelForm):
    text = forms.CharField(
        label=_("Add comment"),
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
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div('text', css_class='form-group-5'),
            Div('attached_file'),
            Div(Submit('save', _('Send')),
                SubmitLink('save-draft', _('Save Draft')),
                css_class="form-group"))
        super().__init__(*args, **kwargs)

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