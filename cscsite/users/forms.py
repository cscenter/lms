from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.contrib.auth.forms import AuthenticationForm
from django.core.urlresolvers import reverse
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
            FormActions(Div(Submit('submit', _("Submit")),
                            css_class="pull-right")))


class UserProfileForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        if kwargs['instance'].is_graduate:
            show_fields = ['photo', 'note', 'csc_review',
                           'yandex_id', 'stepic_id']
        else:
            show_fields = ['photo', 'note', 'yandex_id', 'stepic_id']
        self.helper.layout = Layout(
            Div(*show_fields),
            CANCEL_SAVE_PAIR)

        super(UserProfileForm, self).__init__(*args, **kwargs)

        if 'csc_review' not in show_fields:
            del self.fields['csc_review']

    class Meta:
        model = CSCUser
        fields = ['photo', 'note', 'yandex_id', 'stepic_id', 'csc_review']
        widgets = {
            'note': Ubereditor,
            'csc_review': Ubereditor
        }
        help_texts = {
            'note': LATEX_MARKDOWN_ENABLED,
            'csc_review': LATEX_MARKDOWN_ENABLED,
            'yandex_id': _("<b>YANDEX.ID</b>@yandex.ru"),
            'stepid_id': _("stepic.org/users/<b>424242</b>")
        }
