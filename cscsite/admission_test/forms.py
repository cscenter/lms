# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from crispy_forms.bootstrap import FormActions, PrependedText, InlineRadios
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Row, Submit
from django import forms
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices

from admission_test.models import AdmissionTestApplicant
from users.models import CSCUser, GITHUB_ID_VALIDATOR

ENVELOPE_ICON_HTML = '<i class="fa fa-envelope-o" aria-hidden="true"></i>'
PHONE_ICON_HTML = '<i class="fa fa-mobile" aria-hidden="true"></i>'
COURSES = Choices(('', '', '--------')) + CSCUser.COURSES
WHERE_DID_YOU_LEARN = (
    ('uni', 'плакат/листовка в университете'),
    ('social_net', 'пост в соц. сетях'),
    ('friends', 'от друзей'),
    ('other', 'другое (укажите, что именно, в следующем поле)')
)


class AdmissionTestApplicationForm(forms.ModelForm):
    yandex_id = forms.CharField(
        label='Укажите свой логин на Яндексе',
        help_text=('Например, ваша почта на Яндексе — '
                   '"my.name@yandex.ru", тогда ваш логин — это '
                   '"my.name". Укажите в этом поле именно его.'))
    github_id = forms.CharField(
        label='Укажите свой логин на GitHub, если есть',
        max_length=80,
        validators=[GITHUB_ID_VALIDATOR],
        required=False,
        help_text='https://github.com/XXXX, где XXXX - ваш логин на github.com')

    class Meta:
        model = AdmissionTestApplicant
        fields = ("surname", "first_name", "patronymic", "email",
                  "yandex_id", "stepic_id", "github_id",)
        labels = {
            'email': 'Адрес электронной почты',
            'stepic_id': 'Укажите свой ID на Stepik.org, если есть',
        }
        help_texts = {
            'email': 'На всех этапах приёмной кампании основной способ '
                     'связи с поступающими — электронная почта. Укажите '
                     'тот email, по которому мы быстрее всего сможем с '
                     'вами связаться.',
            'stepic_id': 'https://stepik.org/users/XXXX, где XXXX - ваш Stepik ID',
        }

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Div('surname', css_class='col-xs-4'),
                Div('first_name', css_class='col-xs-4'),
                Div('patronymic', css_class='col-xs-4'),
            ),
            Row(
                Div(PrependedText('email', '@'), css_class='col-xs-8'),
            ),
            Row(
                Div('yandex_id', css_class='col-xs-12'),
            ),
            Row(
                Div('stepic_id', css_class='col-xs-6'),
                Div('github_id', css_class='col-xs-6'),
            ),
            FormActions(Submit('send', _('Send')), css_class="")
        )
        super().__init__(*args, **kwargs)
