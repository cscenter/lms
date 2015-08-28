from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.core.urlresolvers import reverse
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Div
from crispy_forms.bootstrap import FormActions
import floppyforms as forms

from core.forms import Ubereditor
from core.models import LATEX_MARKDOWN_ENABLED
from learning.forms import CANCEL_SAVE_PAIR
from .models import CSCUser, CSCUserReference


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
        if is_valid and settings.SITE_ID == 1:
            user = self.get_user()
            if user.is_curator:
                return is_valid
            user_groups = [g.pk for g in user.groups.all()]
            if CSCUser.group_pks.STUDENT_CLUB in user_groups:
                is_valid = False
                self.add_error(None, ValidationError(_("Students of CS-club can't login on CS-center site")))
        return is_valid


class UserProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)

        self.helper = FormHelper()
        if kwargs['instance'].is_graduate:
            show_fields = ['photo', 'phone', 'note', 'csc_review',
                           'yandex_id', 'github_id', 'stepic_id',
                           'private_contacts']
        else:
            show_fields = ['photo', 'phone', 'note',
                           'yandex_id', 'github_id', 'stepic_id',
                           'private_contacts']

        club_fields = ['first_name', 'last_name', 'patronymic', 'email']
        if kwargs['instance'].is_student_club and \
           not kwargs['instance'].is_student_center:
            show_fields = club_fields + show_fields
        else:
            for field in club_fields:
                del self.fields[field]

        self.helper.layout = Layout(
            Div(*show_fields),
            CANCEL_SAVE_PAIR)

        if 'csc_review' not in show_fields:
            del self.fields['csc_review']

    class Meta:
        model = CSCUser
        fields = ['photo', 'phone', 'note', 'yandex_id', 'github_id',
                  'stepic_id', 'csc_review', 'private_contacts',
                  'first_name', 'last_name', 'patronymic', 'email']
        widgets = {
            'note': Ubereditor,
            'csc_review': Ubereditor,
            'private_contacts': Ubereditor
        }
        help_texts = {
            'note': LATEX_MARKDOWN_ENABLED,
            'csc_review': LATEX_MARKDOWN_ENABLED,
            'private_contacts': (
                "{}; {}"
                .format(LATEX_MARKDOWN_ENABLED,
                        _("will be shown only to logged-in users"))),
            'yandex_id': _("<b>YANDEX.ID</b>@yandex.ru"),
            'github_id': "github.com/<b>GITHUB-ID</b>",
            'stepic_id': _("stepic.org/users/<b>STEPIC-ID</b>")
        }

class CSCUserReferenceCreateForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div('signature',
                'note',
                Div(Div(Submit('save', _('Save'), css_class='pull-right'),
                    css_class='controls'),
                css_class="form-group"))
        )
        super(CSCUserReferenceCreateForm, self).__init__(*args, **kwargs)

    class Meta:
        model = CSCUserReference
        fields = ['signature', 'note']
