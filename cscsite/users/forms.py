from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div
from django import forms
from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, \
    UserCreationForm as _UserCreationForm, UserChangeForm as _UserChangeForm
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import translation
from django.utils.translation import ugettext_lazy as _

from core.models import LATEX_MARKDOWN_ENABLED
from core.utils import is_club_site
from core.widgets import UbereditorWidget
from core.forms import CANCEL_SAVE_PAIR
from learning.settings import AcademicRoles
from users import tasks
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
        # Prevent login for club students on cscenter site
        if is_valid and settings.SITE_ID == settings.CENTER_SITE_ID:
            user = self.get_user()
            if user.is_curator:
                return is_valid
            user_groups = set(g.pk for g in user.groups.all())
            groups_has_access = AcademicRoles.has_access_to_cscenter
            if not user_groups.intersection(groups_has_access):
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
        if kwargs['instance'].is_graduate:
            show_fields = ['phone', 'workplace', 'bio', 'csc_review',
                           'yandex_id', 'github_id', 'stepic_id',
                           'private_contacts']
        else:
            show_fields = ['phone', 'workplace', 'bio',
                           'yandex_id', 'github_id', 'stepic_id',
                           'private_contacts']

        club_fields = ['first_name', 'last_name', 'patronymic']
        if is_club_site():
            show_fields = club_fields + show_fields
            del self.fields["index_redirect"]
        else:
            show_fields.append('index_redirect')
            for field in club_fields:
                del self.fields[field]

        self.helper.layout = Layout(Div(*show_fields), CANCEL_SAVE_PAIR)

        if 'csc_review' not in show_fields:
            del self.fields['csc_review']

    class Meta:
        model = User
        fields = ['phone', 'workplace', 'bio', 'yandex_id', 'github_id',
                  'stepic_id', 'csc_review', 'private_contacts',
                  'first_name', 'last_name', 'patronymic',
                  'index_redirect']
        widgets = {
            'bio': UbereditorWidget,
            'csc_review': UbereditorWidget,
            'private_contacts': UbereditorWidget
        }
        help_texts = {
            'bio': "{}. {}".format(
                _("Tell something about yourself"),
                LATEX_MARKDOWN_ENABLED),
            'csc_review': LATEX_MARKDOWN_ENABLED,
            'private_contacts': (
                "{}; {}"
                .format(LATEX_MARKDOWN_ENABLED,
                        _("will be shown only to logged-in users"))),
            'yandex_id': _("<b>YANDEX.ID</b>@yandex.ru"),
            'github_id': "github.com/<b>GITHUB-ID</b>",
            'stepic_id': _("stepik.org/users/<b>USER_ID</b>"),
            'workplace': _("Specify one or more jobs (comma-separated)")
        }

    def clean_csc_review(self):
        csc_review = self.cleaned_data['csc_review']
        return csc_review.strip()


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
        if u.roles.STUDENT_CENTER in groups:
            if enrollment_year is None:
                self.add_error('enrollment_year', ValidationError(
                    _("Enrollment year should be provided for students")))
        if groups.intersection({AcademicRoles.STUDENT_CENTER,
                                AcademicRoles.VOLUNTEER,
                                AcademicRoles.GRADUATE_CENTER}):
            if not cleaned_data.get('city', ''):
                self.add_error('city', ValidationError(
                    _("Provide city for student")))

        if u.roles.VOLUNTEER in groups and enrollment_year is None:
            self.add_error('enrollment_year', ValidationError(
                _("CSCUser|enrollment year should be provided for volunteers")))

        graduation_year = cleaned_data.get('graduation_year')
        if u.roles.GRADUATE_CENTER in groups and graduation_year is None:
            self.add_error('graduation_year', ValidationError(
                _("CSCUser|graduation year should be provided for graduates")))

        if u.roles.VOLUNTEER in groups and u.roles.STUDENT_CENTER in groups:
            msg = _("User can't be volunteer and student at the same time")
            self.add_error('groups', ValidationError(msg))

        if u.roles.GRADUATE_CENTER in groups and u.roles.STUDENT_CENTER in groups:
            msg = _("User can't be graduated and student at the same time")
            self.add_error('groups', ValidationError(msg))