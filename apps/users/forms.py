from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div
from django import forms
from django.contrib.auth.forms import UserCreationForm as _UserCreationForm, \
    UserChangeForm as _UserChangeForm
from django.utils.translation import ugettext_lazy as _

from core.models import LATEX_MARKDOWN_ENABLED
from core.utils import is_club_site
from core.widgets import UbereditorWidget
from .models import User, EnrollmentCertificate


class UserProfileForm(forms.ModelForm):
    index_redirect = forms.ChoiceField(
        label='Редирект с главной страницы',
        help_text="Выберите раздел, в который вы будете попадать при переходе "
                  "на главную страницу.",
        required=False,
        widget=forms.Select(),)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        option_empty = ('', 'Отключен')
        user_options = self.instance.get_redirect_options()
        self.fields['index_redirect'].choices = [option_empty] + user_options

        self.helper = FormHelper()
        show_fields = ['phone', 'workplace', 'bio',
                       'yandex_id', 'github_id', 'stepic_id',
                       'private_contacts']

        if is_club_site():
            club_fields = ['first_name', 'last_name', 'patronymic']
            show_fields = club_fields + show_fields
        else:
            show_fields.append('index_redirect')
        to_delete = []
        for field_name in self.fields:
            if field_name not in show_fields:
                to_delete.append(field_name)
        for field_name in to_delete:
            del self.fields[field_name]

        self.helper.layout = Layout(Div(*show_fields))
        self.helper.form_tag = False

    class Meta:
        model = User
        fields = ('phone', 'workplace', 'bio', 'yandex_id', 'github_id',
                  'stepic_id', 'private_contacts', 'first_name', 'last_name',
                  'patronymic', 'index_redirect')
        widgets = {
            'bio': UbereditorWidget,
            'private_contacts': UbereditorWidget
        }
        help_texts = {
            'bio': "{}. {}".format(
                _("Tell something about yourself"),
                LATEX_MARKDOWN_ENABLED),
            'private_contacts': (
                "{}; {}"
                .format(LATEX_MARKDOWN_ENABLED,
                        _("will be shown only to logged-in users"))),
            'yandex_id': _("<b>YANDEX.ID</b>@yandex.ru"),
            'github_id': "github.com/<b>GITHUB-ID</b>",
            'stepic_id': _("stepik.org/users/<b>USER_ID</b>"),
            'workplace': _("Specify one or more jobs (comma-separated)")
        }


class EnrollmentCertificateCreateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div('signature',
                'note',
                Div(Div(Submit('save', _('Save'), css_class='pull-right'),
                        css_class='controls'),
                    css_class="form-group"))
        )
        super().__init__(*args, **kwargs)

    class Meta:
        model = EnrollmentCertificate
        fields = ['signature', 'note']


# FIXME: move to admin module
class UserCreationForm(_UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email')


class UserChangeForm(_UserChangeForm):
    class Meta:
        fields = '__all__'
        model = User
