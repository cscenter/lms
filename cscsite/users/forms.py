from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import ugettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout, Submit, Hidden, Button, Div
from crispy_forms.bootstrap import FormActions
import floppyforms as forms

from core.forms import Ubereditor
from learning.models import LATEX_MARKDOWN_ENABLED
from learning.forms import CANCEL_SAVE_PAIR

from .models import CSCUser


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
        self.helper = FormHelper()
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-xs-2'
        self.helper.field_class = 'col-xs-7'
        self.helper.layout = Layout(
            'username',
            'password',
            FormActions(Submit('submit', _("Submit"),
                               css_class="pull-right")))


class UserProfileForm(forms.ModelForm):
    note = forms.CharField(
        label=_("Description"),
        help_text=LATEX_MARKDOWN_ENABLED,
        widget=Ubereditor)

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div('note'),
            CANCEL_SAVE_PAIR)
        super(UserProfileForm, self).__init__(*args, **kwargs)

    class Meta:
        model = CSCUser
        fields = ['note']
