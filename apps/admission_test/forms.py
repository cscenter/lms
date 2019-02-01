# -*- coding: utf-8 -*-

from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Row, Submit, HTML, Field
from django import forms
from django.utils.translation import ugettext_lazy as _

from admission_test.models import AdmissionTestApplicant
from admission_test.tasks import register_in_yandex_contest
from core.urls import reverse


class AdmissionTestApplicationForm(forms.ModelForm):
    yandex_id = forms.CharField(
        label='Укажите свой логин на Яндексе',
        help_text=('Например, ваша почта на Яндексе — '
                   '"my.name@yandex.ru", тогда ваш логин — это '
                   '"my.name". Укажите в этом поле именно его.'))

    class Meta:
        model = AdmissionTestApplicant
        fields = ("surname", "first_name", "patronymic", "email",
                  "yandex_id",)
        labels = {
            'email': 'Адрес электронной почты',
        }
        help_texts = {
            'email': '',
        }

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        yandex_passport = kwargs.pop("yandex_passport_access_allowed", None)
        url = reverse("admission_test:auth_begin")
        if yandex_passport:
            yandex_button = f'<a class="btn btn-default __auth-begin" href="{url}" disabled="disabled"><i class="fa fa-check text-success"></i> Доступ разрешен</a>'
        else:
            yandex_button = f'<a class="btn btn-default __auth-begin" href="{url}">Разрешить доступ к данным на Яндексе</a>'
        self.helper.layout = Layout(
            Row(Div(Field('surname', placeholder=_("Surname")), css_class='col-xs-12')),
            Row(Div(Field('first_name', placeholder=_("First name")), css_class='col-xs-12')),
            Row(Div(Field('patronymic', placeholder=_("Patronymic")), css_class='col-xs-12')),
            Row(Div(Field('email', placeholder=_("Email")), css_class='col-xs-12')),
            HTML(f"""
            <div class="row">
                <div class="col-xs-12 form-group">
                    <div class="controls">
                        {yandex_button}
                        <div class="btn btn-sm" tabindex="0" role="button" data-toggle="popover" data-trigger="focus"
                            data-content="Пробный контест организован в системе Яндекс.Контест.<br>Чтобы выдать права участника, нам нужно знать ваш логин на Яндексе без ошибок, учитывая все особенности, например, вход через социальные сети.<br>Чтобы всё сработало, поделитесь с нами доступом к некоторым данным из вашего Яндекс.Паспорта: логин, ФИО.">
                            <i class="fa fa-2x fa-question-circle-o"></i>
                        </div>
                    </div>
                </div>
            </div>
            """),
            FormActions(Submit('send', _('Send')), css_class="")
        )
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit)
        register_in_yandex_contest.delay(instance.pk)
        return instance
