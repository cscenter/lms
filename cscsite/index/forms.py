from __future__ import absolute_import, unicode_literals

from django.utils.translation import ugettext as _

import floppyforms.__future__ as forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit


class UnsubscribeForm(forms.Form):
    sub_hash = forms.CharField(required=True, max_length=32,
                               widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        super(UnsubscribeForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.add_input(Submit('submit', _("Ya|Unsubscribe")))
