from __future__ import absolute_import, unicode_literals

from django.contrib.auth.forms import AuthenticationForm
from django.core.urlresolvers import reverse
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
            _("You can also <a href=\"{0}\">reset your password</a>")
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


class UserProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        if kwargs['instance'].is_graduate:
            show_fields = ['photo', 'note', 'csc_review',
                           'yandex_id', 'github_id', 'stepic_id',
                           'private_contacts']
        else:
            show_fields = ['photo', 'note',
                           'yandex_id', 'github_id', 'stepic_id',
                           'private_contacts']
        self.helper.layout = Layout(
            Div(*show_fields),
            CANCEL_SAVE_PAIR)

        super(UserProfileForm, self).__init__(*args, **kwargs)

        if 'csc_review' not in show_fields:
            del self.fields['csc_review']

    class Meta:
        model = CSCUser
        fields = ['photo', 'note', 'yandex_id', 'github_id', 'stepic_id',
                  'csc_review', 'private_contacts']
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
