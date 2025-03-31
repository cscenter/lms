from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Layout, Submit

from django import forms
from django.contrib.auth.forms import UserChangeForm as _UserChangeForm
from django.contrib.auth.forms import UserCreationForm as _UserCreationForm
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from core.models import LATEX_MARKDOWN_ENABLED
from core.utils import is_club_site
from core.urls import reverse_lazy
from core.widgets import DateInputTextWidget, UbereditorWidget

from .models import CertificateOfParticipation, User


class UserProfileForm(forms.ModelForm):
    index_redirect = forms.ChoiceField(
        label='Редирект с главной страницы',
        help_text="Выберите раздел, в который вы будете попадать при переходе "
                  "на главную страницу.",
        required=False,
        widget=forms.Select(),)
    birth_date = forms.DateField(
        label=_("Date of Birth"),
        help_text=_("Format: dd.mm.yyyy"),
        required=False,
        widget=DateInputTextWidget(attrs={'class': 'datepicker'})
    )

    def __init__(self, *args, **kwargs):
        self.editor = kwargs.pop('editor')
        self.student = kwargs.pop('student')
        super().__init__(*args, **kwargs)
        option_empty = ('', 'Отключен')
        user_options = self.instance.get_redirect_options()
        self.fields['index_redirect'].choices = [option_empty] + user_options
        self.helper = FormHelper()
        show_fields = list(UserProfileForm.Meta.fields)
        self.fields['birth_date'].disabled = True
        if is_club_site():
            show_fields.extend(['first_name', 'last_name', 'patronymic'])
        else:
            show_fields.extend(['index_redirect', 'social_networks'])

        self.helper.layout = Layout(Div(*show_fields))
        self.helper.form_tag = False


    class Meta:
        model = User
        fields = ('birth_date', 'phone', 'workplace', 'bio', 'time_zone',
                  'telegram_username', 'github_login', 'stepic_id', 'codeforces_login',
                  'private_contacts', 'is_notification_allowed', 'tshirt_size')
        widgets = {
            'bio': UbereditorWidget,
            'private_contacts': UbereditorWidget,
            'social_networks': UbereditorWidget,
        }
        help_texts = {
            'bio': "{}. {}".format(
                _("Tell something about yourself"),
                LATEX_MARKDOWN_ENABLED),
            'private_contacts': (
                "{}; {}"
                .format(LATEX_MARKDOWN_ENABLED,
                        _("will be shown only to logged-in users"))),
            'telegram_username': '@&lt;<b>username</b>&gt; в настройках профиля Telegram',
            'github_login': "github.com/<b>GITHUB-ID</b>",
            'stepic_id': _("stepik.org/users/<b>USER_ID</b>"),
            'codeforces_login': _("codeforces.com/profile/<b>HANDLE</b>"),
            'workplace': _("Specify one or more jobs (comma-separated)"),
            'is_notification_allowed': _("Не касается уведомлений аутентификации")
        }


class CertificateOfParticipationCreateForm(forms.ModelForm):
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
        model = CertificateOfParticipation
        fields = ['signature', 'note']
        help_texts = {
            'signature': 'Укажите ФИО студента на латинице (необходимо для английской версии справки).',
            'note': 'Дополнительная информация'
        }


class UserCreationForm(_UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'branch', 'gender', 'time_zone')


class UserChangeForm(_UserChangeForm):
    class Meta:
        fields = '__all__'
        model = User
