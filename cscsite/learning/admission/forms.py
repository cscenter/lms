# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from crispy_forms.bootstrap import FormActions, PrependedText, InlineRadios
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, Field, Row, Fieldset, \
    MultiField
from django import forms
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.forms.models import ModelForm
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices

from core.forms import Ubereditor
from core.views import ReadOnlyFieldsMixin
from learning.admission.models import Interview, Comment, Applicant
from users.models import CSCUser

ENVELOPE_ICON_HTML = '<i class="fa fa-envelope-o" aria-hidden="true"></i>'
PHONE_ICON_HTML = '<i class="fa fa-mobile" aria-hidden="true"></i>'
COURSES = Choices(('', '', '--------')) + CSCUser.COURSES
WHERE_DID_YOU_LEARN = (
    ('uni', 'плакат/листовка в университете'),
    ('social_net', 'пост в соц. сетях'),
    ('friends', 'от друзей'),
    ('other', 'другое (укажите, что именно, в следующем поле)')
)


class ApplicationFormStep1(forms.ModelForm):
    city = forms.ChoiceField(
        widget=forms.RadioSelect(),
        choices=(
            ("spb", _("St Petersburg")),
            ("nsk", _("Novosibirsk")),
        ),
        label='Выберите город, в котором вы живёте и куда хотите поступить',
        help_text='С 2017 года CS центр есть не только в Санкт-Петербурге, '
                  'но и в Новосибирске.'
    )

    class Meta:
        model = Applicant
        fields = ("city", "second_name", "first_name", "last_name", "email",
                  "phone")
        help_texts = {
            'email': 'На всех этапах приёмной кампании основной способ '
                     'связи с поступающими — электронная почта. Укажите '
                     'тот email, по которому мы быстрее всего сможем с '
                     'вами связаться.',
            'phone': ''
        }
        labels = {
            'email': 'Адрес электронной почты'
        }

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            InlineRadios('city'),
            Row(
                Div('second_name', css_class='col-xs-4'),
                Div('first_name', css_class='col-xs-4'),
                Div('last_name', css_class='col-xs-4'),
            ),
            Row(
                Div(PrependedText('email', '@'), css_class='col-xs-8'),
                Div('phone', css_class='col-xs-4')
            )

        )
        super().__init__(*args, **kwargs)


class ApplicationInSpbForm(forms.ModelForm):
    has_job = forms.ChoiceField(
        label='Вы сейчас работаете?',
        choices=(("Нет", "Нет"), ("Да", "Да")))
    yandex_id = forms.CharField(
        label='Укажите свой логин на Яндексе',
        help_text=('Например, ваша почта на Яндексе — '
                   '"my.name@yandex.ru", тогда ваш логин — это '
                   '"my.name". Укажите в этом поле именно его.'))
    course = forms.ChoiceField(label='Курс, на котором вы учитесь',
                               choices=COURSES)
    where_did_you_learn = forms.MultipleChoiceField(
        label='Откуда вы узнали о CS центре?',
        help_text='Вы можете выбрать несколько вариантов ответа, если '
                  'источников больше одного',
        choices=WHERE_DID_YOU_LEARN,
        widget=forms.CheckboxSelectMultiple
    )
    preferred_study_programs = forms.MultipleChoiceField(
        label='Какие направления обучения из трёх вам интересны в CS центре?',
        choices=(
            ("dm", "Анализ Данных"),
            ("cs", "Современная информатика"),
            ("se", "Разработка ПО")
        ),
        help_text='Мы не просим поступающих определиться с направлением '
                  'обучения, будучи студентом вам предстоит сделать этот выбор '
                  'через год-полтора после поступления, а сейчас предлагаем '
                  'указать одно или несколько направлений, которые кажутся вам '
                  'интересными.',
        widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Applicant
        fields = ("university", "university_other",
                  "faculty", "course", "has_job", "workplace", "position",
                  "experience", "yandex_id", "stepic_id", "github_id",
                  "preferred_study_programs", "where_did_you_learn",
                  "motivation", "your_future_plans",
                  "additional_info")
        labels = {
            'university': 'Университет (и иногда факультет)',
            'university_other': 'Название университета',
            'faculty': 'Факультет, специальность или кафедра',
            'experience': 'Расскажите о своём опыте программирования и '
                          'исследований',
            'stepic_id': 'Укажите свой ID на Stepik.org, если есть',
            'github_id': 'Укажите свой логин на GitHub, если есть',
            'motivation': 'Почему вы хотите учиться в CS центре?',
            'your_future_plans': 'Чем вы планируете заниматься после '
                                 'окончания обучения?',
            'additional_info': 'Напишите любую дополнительную информацию о '
                               'себе, которую хотите указать',


        }
        help_texts = {
            'university': 'В котором вы учитесь или который закончили',
            'university_other': 'Заполните, если в поле слева указали "Другое".',
            'faculty': '',
            'experience': 'Напишите здесь о том, что вы делаете на работе, '
                          'и о своей нынешней дипломной или курсовой работе. '
                          'Здесь стоит рассказать о студенческих проектах, '
                          'в которых вы участвовали, или о небольших личных '
                          'проектах, которые вы делаете дома, для своего '
                          'удовольствия.',

            'stepic_id': 'Если ссылка на ваш профиль на Stepik выглядит вот '
                         'так: https://stepik.org/users/XXXX, то ID — это XXXX',
            'github_id': 'Если ссылка на ваш профиль на GitHub выглядит вот '
                         'так: https://github.com/XXXX, то логин — это XXXX',
            'workplace': '',
            'position': '',
            'where_did_you_learn': 'Вы можете выбрать несколько вариантов '
                                   'ответа, если источников больше одного.',
            'motivation': '',
            'your_future_plans': '',
            'additional_info': ''
        }
        widgets = {
            'faculty': forms.TextInput(),
            'motivation': forms.Textarea(attrs={"rows": 6}),
            'your_future_plans': forms.Textarea(attrs={"rows": 6}),
            'additional_info': forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Div('university', css_class='col-xs-6'),
                Div('university_other', css_class='col-xs-6'),
            ),
            Row(
                Div('faculty', css_class='col-xs-6'),
                Div('course', css_class='col-xs-6')
            ),
            Row(
                Div('has_job', css_class='col-xs-4'),
                Div('workplace', css_class='col-xs-4'),
                Div('position', css_class='col-xs-4'),
            ),
        )
        super().__init__(*args, **kwargs)
        # Hide some fields if they are not necessary at the moment
        if not self.is_bound:
            self.fields['university_other'].disabled = True
        if 'spb-has_job' not in self.data or self.data['spb-has_job'] == 'Нет':
            self.fields['workplace'].disabled = True
            self.fields['position'].disabled = True


class ApplicationInNskForm(forms.ModelForm):
    preferred_study_programs = forms.MultipleChoiceField(
        label='Какие направления обучения из двух вам интересны в CS центре?',
        choices=(
            ("dm", "Анализ Данных"),
            ("se", "Разработка ПО")
        ),
        help_text='Мы не просим поступающих определиться с направлением '
                  'обучения, будучи студентом вам предстоит сделать этот выбор '
                  'через год-полтора после поступления, а сейчас предлагаем '
                  'указать одно или несколько направлений, которые кажутся вам '
                  'интересными.',
        widget=forms.CheckboxSelectMultiple
    )

    class Meta(ApplicationInSpbForm.Meta):
        fields = ("university", "stepic_id", "yandex_id", "github_id",)


class InterviewForm(forms.ModelForm):
    class Meta:
        model = Interview
        fields = "__all__"
        widgets = {
            'applicant': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super(InterviewForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(
            FormActions(Submit('create', _('Create interview')),
                        css_class="pull-right"))


class InterviewCommentForm(forms.ModelForm):

    class Meta:
        model = Comment
        fields = ["text", "score", "interview", "interviewer"]
        widgets = {
            'interview': forms.HiddenInput(),
            'interviewer': forms.HiddenInput(),
            'score': forms.Select(choices=(
                ("", ""),
                (-2, "не брать ни сейчас, ни потом"),
                (-1, "не брать сейчас"),
                (0, "нейтрально"),
                (1, "можно взять"),
                (2, "точно нужно взять"))),
            'text': Ubereditor(attrs={
                'data-local-persist': 'true',
            })
        }

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div('text'),
            Div(
                Div('score', css_class='col-xs-6'),
                Div(Submit('save', _('Save'), css_class='pull-right'),
                    css_class='col-xs-6'),
                css_class="row")
        )
        self.interviewer = kwargs.pop("interviewer", None)
        self.interview_id = kwargs.pop("interview_id", None)
        super(InterviewCommentForm, self).__init__(*args, **kwargs)
        self.fields['score'].label = "Выберите оценку"

    def clean_interviewer(self):
        interviewer = self.cleaned_data['interviewer']
        if not self.interviewer or (interviewer != self.interviewer and not
                                    self.interviewer.is_curator):
            raise ValidationError(
                _("Sorry, but you should be in interviewers list to "
                  "create or update comment."))
        return interviewer

    def clean_interview(self):
        interview = self.cleaned_data['interview']
        if str(interview.pk) != self.interview_id:
            raise ValidationError(
                "Submitted interview id not match GET-value")
        return interview


class ApplicantReadOnlyForm(ReadOnlyFieldsMixin, forms.ModelForm):
    readonly_fields = "__all__"

    class Meta:
        model = Applicant
        exclude = ("campaign", "first_name", "last_name", "second_name",
                   "status", "admin_note", "yandex_id_normalize", "user")


class ApplicantStatusForm(forms.ModelForm):
    class Meta:
        model = Applicant
        fields = ("admin_note", "status")

    def __init__(self, *args, **kwargs):
        super(ApplicantStatusForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(
            FormActions(Submit('update', _('Update')), css_class="pull-right"))
        self.helper.form_action = "{}{}".format(
            reverse("admission_applicant_status_update", args=[self.instance.pk]),
            "#update-status-form")


INTERVIEW_RESULTS_CHOICES = (
    ("", "------"),
    (Applicant.ACCEPT, "Берём"),
    (Applicant.VOLUNTEER, "Берём в вольные слушатели"),
    (Applicant.ACCEPT_IF, "Берём с условием"),
    (Applicant.REJECTED_BY_INTERVIEW, "Не берём"),
    (Applicant.THEY_REFUSED, "Отказался"),
)


class InterviewResultsModelForm(ModelForm):
    """
    In `InterviewResultsView` we use Interview manager
    to retrieve data, because one applicant can have many interviews,
    but in fact we want to update applicant model.
    """
    class Meta:
        model = Applicant
        fields = ("status",)
        # FIXME: don't know why widget override doesn't work here

    status = forms.ChoiceField(choices=INTERVIEW_RESULTS_CHOICES,
                               required=False,
                               initial="")

    def clean_status(self):
        """Save old status if none provided"""
        data = self.cleaned_data["status"]
        if not data:
            return self.instance.status
        return data
