from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div
from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, \
    UserCreationForm as _UserCreationForm, UserChangeForm as _UserChangeForm
from django.core.exceptions import ValidationError
from django.utils import translation
from django.utils.translation import ugettext_lazy as _

from core.forms import CANCEL_SAVE_PAIR
from core.models import LATEX_MARKDOWN_ENABLED
from core.urls import reverse
from core.utils import is_club_site
from core.widgets import UbereditorWidget
from users import tasks
from users.constants import AcademicRoles, CSCENTER_ACCESS_ALLOWED
from .models import User, EnrollmentCertificate


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        required=True,
        label=_("Username"),
        widget=forms.TextInput(attrs={'autofocus': 'autofocus'}))
    password = forms.CharField(
        widget=forms.PasswordInput,
        label=_("Password"))

    def __init__(self, *args, **kwargs):
        super(LoginForm, self).__init__(*args, **kwargs)
        # NOTE(Dmitry): this should be done after Users app is loaded
        # because of URL name resolutions quirks
        self.fields['password'].help_text = (
            _("You can also <a href=\"{0}\">restore your password</a>")
            .format(reverse('password_reset')))
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-xs-2'
        self.helper.field_class = 'col-xs-7'
        self.helper.layout = Layout(
            'username',
            'password',
            FormActions(Div(Submit('submit', _("Login")),
                            css_class="pull-right")))

    def is_valid(self):
        is_valid = super(LoginForm, self).is_valid()
        # Prevent login for club students on compscicenter.ru
        if is_valid and settings.SITE_ID == settings.CENTER_SITE_ID:
            user = self.get_user()
            if user.is_curator:
                return is_valid
            user_roles = set(g.role for g
                             in user.groups.filter(site_id=settings.SITE_ID))
            if not user_roles.intersection(CSCENTER_ACCESS_ALLOWED):
                is_valid = False
                no_access_msg = _("You haven't enough access rights to login "
                                  "on this site. Contact curators if you think "
                                  "this is wrong.")
                self.add_error(None, ValidationError(no_access_msg))
        return is_valid


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


class UserPasswordResetForm(PasswordResetForm):
    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        ctx = {
            'site_name': context['site_name'],
            'email': context['email'],
            'protocol': context['protocol'],
            'domain': context['domain'],
            'uid': context['uid'],
            'token': context['token'],
        }
        tasks.send_restore_password_email.delay(
            from_email=from_email,
            to_email=to_email,
            context=ctx,
            language_code=translation.get_language())


class UserCreationForm(_UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email')


class UserChangeForm(_UserChangeForm):
    class Meta:
        fields = '__all__'
        model = User

    def clean(self):
        """XXX: we can't validate m2m like `groups` in Model.clean() method"""
        cleaned_data = super().clean()
        enrollment_year = cleaned_data.get('enrollment_year')
        groups = {x.pk for x in cleaned_data.get('groups', [])}
        u: User = self.instance
        # FIXME: How to check these invariants with 1-to-many relation?
        if u.roles.VOLUNTEER in groups and u.roles.STUDENT_CENTER in groups:
            msg = _("User can't be volunteer and student at the same time")
            self.add_error('groups', ValidationError(msg))

        if u.roles.GRADUATE_CENTER in groups and u.roles.STUDENT_CENTER in groups:
            msg = _("User can't be graduated and student at the same time")
            self.add_error('groups', ValidationError(msg))