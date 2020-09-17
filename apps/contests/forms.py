from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout
from django import forms
from django.utils.translation import gettext_lazy as _

from contests.models import YandexCompilers, Submission, CheckingSystemTypes, \
    CheckingSystem
from contests.utils import resolve_problem_id


class CheckingSystemForm(forms.ModelForm):
    type = forms.ChoiceField(
        label=_("Checking System Type"),
        choices=CheckingSystemTypes.choices
    )
    url = forms.URLField(
        label=_("Checking System URL"),
        help_text=_("Paste URL of the Yandex.Contest problem"),
        required=False
    )

    class Meta:
        model = CheckingSystem
        fields = ('type', 'url', 'settings')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div('type', css_class='form-group-5'),
            Div('url', css_class='form-group-5')
        )

    def clean_settings(self):
        contest_id, problem_id = resolve_problem_id(self.cleaned_data['url'])
        return {'contest_id': contest_id, 'problem_id': problem_id}


class YandexContestSubmissionForm(forms.ModelForm):
    settings = forms.ChoiceField(
        label=_("Compiler"),
        choices=YandexCompilers.choices
    )

    class Meta:
        model = Submission
        fields = ('settings',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div('settings', css_class='form-group-5'),
        )

    def clean_settings(self):
        compiler_id = self.cleaned_data['settings']
        return {'compiler_id': compiler_id}

