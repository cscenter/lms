# -*- coding: utf-8 -*-

from datetime import datetime

from crispy_forms.bootstrap import FormActions, InlineRadios
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit, Field, Row, HTML
from django import forms
from django.core.exceptions import ValidationError, NON_FIELD_ERRORS
from django.forms import SelectMultiple
from django.forms.models import ModelForm
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django_filters.conf import settings as filters_settings

from admission.models import Interview, Comment, Applicant, \
    InterviewAssignment, InterviewSlot, InterviewStream
from core.models import University
from core.timezone import now_local
from core.urls import reverse
from core.views import ReadOnlyFieldsMixin
from core.widgets import UbereditorWidget
from learning.settings import AcademicDegreeYears
from users.models import GITHUB_LOGIN_VALIDATOR

DEGREE_YEAR_CHOICES = ('', '', '--------') + AcademicDegreeYears.choices
WHERE_DID_YOU_LEARN = (
    ('uni', 'плакат/листовка в университете'),
    ('social_net', 'пост в соц. сетях'),
    ('friends', 'от друзей'),
    ('other', 'другое')
)


class CampaignChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return obj.city


class ApplicationFormStep1(forms.ModelForm):
    campaign = CampaignChoiceField(
        label='Выберите город, в котором вы живёте и куда хотите поступить',
        queryset=None,
        empty_label=None
    )
    yandex_id = forms.CharField(
        label='Укажите свой логин на Яндексе',
        help_text=('Например, ваша почта на Яндексе — '
                   '"my.name@yandex.ru", тогда ваш логин — это '
                   '"my.name". Укажите в этом поле именно его.'))
    github_id = forms.CharField(
        label='Логин на GitHub',
        max_length=80,
        validators=[GITHUB_LOGIN_VALIDATOR],
        required=False,
        help_text='Если ссылка на ваш профиль на GitHub выглядит вот '
                  'так: https://github.com/XXXX, то логин — это XXXX')

    class Meta:
        model = Applicant
        fields = ("campaign", "surname", "first_name", "patronymic", "email",
                  "phone", "yandex_id", "stepic_id", "github_id",)
        labels = {
            'email': 'Адрес электронной почты',
            'stepic_id': 'ID на Stepik.org',
        }
        help_texts = {
            'email': '',
            'phone': '',
            'stepic_id': 'https://stepik.org/users/XXXX, XXXX - это ваш ID',
        }
        error_messages = {
            NON_FIELD_ERRORS: {
                'unique_together': "Если вы уже зарегистрировали анкету на "
                                   "указанный email и хотите внести изменения, "
                                   "напишите на info@compscicenter.ru с этой почты.",
            }
        }

    def __init__(self, *args, **kwargs):
        yandex_passport = kwargs.pop("yandex_passport_access_allowed", None)
        url = reverse("admission:auth_begin")
        if yandex_passport:
            yandex_button = f'''
<a class="btn btn-default __login-access-begin" href="{url}" disabled="disabled">
    <i class="fa fa-check text-success"></i> Доступ разрешен
</a>'''.strip()
        else:
            yandex_button = f'''
<a class="btn btn-default __login-access-begin" href="{url}">
    Разрешить доступ к данным
</a>'''.strip()
        self.helper = FormHelper()
        self.helper.layout = Layout(
            InlineRadios('campaign'),
            Row(
                Div('surname', css_class='col-sm-4'),
                Div('first_name', css_class='col-sm-4'),
                Div('patronymic', css_class='col-sm-4'),
            ),
            Row(
                Div('email', css_class='col-sm-8'),
                Div('phone', css_class='col-sm-4')
            ),
            HTML(f"""
                <div class="row">
                    <div class="col-xs-12 form-group">
                        <label for="id_welcome-yandex_id" class="control-label requiredField">Доступ к данным на Яндексе<span class="asteriskField">*</span></label>
                        <div class="controls">
                            {yandex_button}
                            <div class="btn btn-sm" tabindex="0" role="button" data-toggle="popover" data-trigger="focus"
                                data-content="Вступительный тест организован в системе Яндекс.Контест. Чтобы выдать права участника и затем сопоставить результаты с анкетами, нам нужно знать ваш логин на Яндексе без ошибок, учитывая все особенности, например, вход через социальные сети. Чтобы всё сработало, поделитесь с нами доступом к некоторым данным из вашего Яндекс.Паспорта: логин и ФИО.">
                                <i class="fa fa-2x fa-question-circle-o"></i>
                            </div>
                        </div>
                    </div>
                </div>
                """),
            Row(
                Div('stepic_id', css_class='col-sm-6'),
                Div('github_id', css_class='col-sm-6'),
            ),
        )
        campaigns_qs = kwargs.pop("campaigns_qs", None)
        super().__init__(*args, **kwargs)
        self.fields['campaign'].queryset = campaigns_qs

    def clean(self):
        cleaned_data = super().clean()
        yandex_login = self.cleaned_data.get("yandex_id", None)
        if not yandex_login:
            raise ValidationError("Не был получен доступ к данным на Яндексе.")
        return cleaned_data


class ApplicationFormStep2(forms.ModelForm):
    has_job = forms.TypedChoiceField(
        label='Вы сейчас работаете?',
        coerce=lambda x: x == 'yes',
        choices=[('no', 'Нет'), ('yes', 'Да')],
        widget=forms.RadioSelect
    )
    course = forms.ChoiceField(label='Курс, на котором вы учитесь',
                               choices=DEGREE_YEAR_CHOICES)
    where_did_you_learn = forms.MultipleChoiceField(
        label='Откуда вы узнали о CS центре?',
        choices=WHERE_DID_YOU_LEARN,
        widget=forms.CheckboxSelectMultiple
    )
    motivation = forms.CharField(
        label='Почему вы хотите учиться в CS центре?',
        required=True,
        widget=forms.Textarea(attrs={"rows": 6}))

    class Meta:
        model = Applicant
        fields = ("university", "university_other",
                  "faculty", "course", "has_job", "workplace", "position",
                  "experience",  "preferred_study_programs",
                  "preferred_study_programs_dm_note",
                  "preferred_study_programs_cs_note",
                  "preferred_study_programs_se_note",
                  "where_did_you_learn", "where_did_you_learn_other",
                  "motivation", "your_future_plans",
                  "additional_info")
        labels = {
            'university_other': 'Введите название университета',
            'faculty': 'Факультет, специальность или кафедра',
            'experience': 'Расскажите о своём опыте программирования и '
                          'исследований',
            'preferred_study_programs_dm_note': 'Почему вам интересен анализ '
                                                'данных? Какие повседневные '
                                                'задачи решаются с помощью '
                                                'анализа данных?',
            'preferred_study_programs_se_note': 'В разработке какого приложения,'
                                                ' которым вы пользуетесь каждый '
                                                'день, вы хотели бы принять '
                                                'участие? Почему? Каких знаний '
                                                'вам для этого не хватает?',
            'your_future_plans': 'Чем вы планируете заниматься после '
                                 'окончания обучения?',
            'additional_info': 'Напишите любую дополнительную информацию о '
                               'себе, которую хотите указать',
            'where_did_you_learn_other': 'Откуда вы узнали о CS центре? (ваш вариант)'


        }
        help_texts = {
            'university_other': '',
            'faculty': '',
            'workplace': '',
            'position': '',
            'experience': '',
            'preferred_study_programs_dm_note': '',
            'preferred_study_programs_se_note': '',
            'where_did_you_learn': '',
            'your_future_plans': '',
            'additional_info': ''
        }
        widgets = {
            'faculty': forms.TextInput(),
            'experience': forms.Textarea(attrs={"rows": 6}),
            'preferred_study_programs_dm_note': forms.Textarea(attrs={"rows": 6}),
            'preferred_study_programs_cs_note': forms.Textarea(attrs={"rows": 6}),
            'preferred_study_programs_se_note': forms.Textarea(attrs={"rows": 6}),
            'your_future_plans': forms.Textarea(attrs={"rows": 6}),
            'additional_info': forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop("yandex_passport_access_allowed", None)
        if not self.CITY_CODE:
            raise ValueError("Provide city code prefix")
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Div("university", css_class='col-sm-8'),
            ),
            Row(
                Div('university_other', css_class='col-sm-8'),
                css_class='margin-bottom-15',
                css_id='university-other-row',
            ),
            Row(
                Div('faculty', css_class='col-sm-8'),
            ),
            Row(
                Div('course', css_class='col-sm-4'),
                css_class='margin-bottom-15',
            ),
            Row(
                Div(InlineRadios('has_job'), css_class='col-sm-4'),
            ),
            Row(
                Div('workplace', css_class='col-sm-4'),
                Div('position', css_class='col-sm-4'),
                css_class='margin-bottom-15',
                css_id='job-details-row'
            ),
            Row(
                Div(Field('experience',
                          placeholder='Напишите здесь о том, что вы делаете на работе, '
                          'и о своей нынешней дипломной или курсовой работе. '
                          'Здесь стоит рассказать о студенческих проектах, '
                          'в которых вы участвовали, или о небольших личных '
                          'проектах, которые вы делаете дома, для своего '
                          'удовольствия.'), css_class='col-sm-12'),
                css_class='margin-bottom-15'
            ),
            Row(
                Div(Field('preferred_study_programs',
                          template="admission/forms/checkboxselectmultiple.html"), css_class='col-sm-12'),
                Div('preferred_study_programs_dm_note', css_class='col-sm-12'),
                Div('preferred_study_programs_cs_note', css_class='col-sm-12'),
                Div('preferred_study_programs_se_note', css_class='col-sm-12'),
                css_class='margin-bottom-15',
                css_id="study-programs-row"
            ),
            Row(
                Div('motivation', css_class='col-sm-12'),
            ),
            Row(
                Div('your_future_plans', css_class='col-sm-12'),
            ),
            Row(
                Div('additional_info', css_class='col-sm-12'),
            ),
            Row(
                Div('where_did_you_learn', css_class='col-sm-12'),
                Div('where_did_you_learn_other', css_class='col-sm-12'),
                css_class='margin-bottom-15',
                css_id="where-did-you-learn-row"
            ),
        )
        super().__init__(*args, **kwargs)
        # Tricky part. We should retrieve row with `preferred_study_programs`
        # id and hide other optional related fields if necessary
        areas_of_study_fieldset = next((f for f in self.helper.layout.fields
                                        if f.css_id == "study-programs-row"),
                                       None)
        # Hide fields if they are not necessary at the moment
        if not self.is_bound:
            for row in areas_of_study_fieldset:
                field_names = (fn for _, fn in row.get_field_names())
                if 'preferred_study_programs' not in field_names:
                    row.css_class += ' hidden'
        else:
            target = self.CITY_CODE + "-preferred_study_programs"
            selected_areas = self.data.getlist(target)
            for row in areas_of_study_fieldset:
                field_names = (fn for _, fn in row.get_field_names())
                if 'preferred_study_programs' in field_names:
                    continue
                selected = False
                for area in selected_areas:
                    input_name = f"preferred_study_programs_{area}_note"
                    if input_name in row:
                        selected = True
                        break
                if not selected:
                    row.css_class += ' hidden'

        # University other visibility
        target = self.CITY_CODE + "-university"
        if (target not in self.data or
                self.data[target] != str(self.UNIVERSITY_OTHER_ID)):
            fieldset = next((f for f in self.helper.layout.fields
                             if f.css_id == "university-other-row"), None)
            if fieldset:
                fieldset.css_class += ' hidden'
        # Has job visibility
        target = self.CITY_CODE + "-has_job"
        if target not in self.data or self.data[target] == 'no':
            fieldset = next((f for f in self.helper.layout.fields
                             if f.css_id == "job-details-row"), None)
            if fieldset:
                fieldset.css_class += ' hidden'
        # Where did you learn
        target = self.CITY_CODE + "-where_did_you_learn"
        if target not in self.data or "other" not in self.data.getlist(target):
            fieldset = next((f for f in self.helper.layout.fields
                             if f.css_id == "where-did-you-learn-row"), None)
            if fieldset:
                for row in fieldset:
                    if 'where_did_you_learn' not in row:
                        row.css_class += ' hidden'


class ApplicationInSpbForm(ApplicationFormStep2):
    CITY_CODE = "spb"
    UNIVERSITY_OTHER_ID = 10
    university = forms.ModelChoiceField(
        label='Университет (и иногда факультет), в котором вы учитесь или '
              'который закончили',
        queryset=University.objects.filter(city__code=CITY_CODE).order_by("sort"),
        help_text=''
    )
    preferred_study_programs = forms.MultipleChoiceField(
        label='Какие направления обучения из трёх вам интересны в CS центре?',
        choices=Applicant.STUDY_PROGRAMS,
        help_text='Мы не просим поступающих сразу определиться с направлением '
                  'обучения. Вам предстоит сделать этот выбор '
                  'через год-полтора после поступления. Сейчас мы предлагаем '
                  'указать одно или несколько направлений, которые кажутся вам '
                  'интересными.',
        widget=forms.CheckboxSelectMultiple
    )


class ApplicationInNskForm(ApplicationFormStep2):
    CITY_CODE = "nsk"
    UNIVERSITY_OTHER_ID = 14
    university = forms.ModelChoiceField(
        label='Университет, в котором вы учитесь или который закончили',
        queryset=University.objects.filter(city__code=CITY_CODE).order_by("sort"),
        help_text=''
    )
    preferred_study_programs = forms.MultipleChoiceField(
        label='Какие направления обучения из двух вам интересны в CS центре?',
        choices=(
            (Applicant.STUDY_PROGRAM_DS, "Анализ данных"),
            (Applicant.STUDY_PROGRAM_SE, "Разработка ПО")
        ),
        help_text='Мы не просим поступающих сразу определиться с направлением '
                  'обучения. Вам предстоит сделать этот выбор '
                  'через год-полтора после поступления. Сейчас мы предлагаем '
                  'указать одно или несколько направлений, которые кажутся вам '
                  'интересными.',
        widget=forms.CheckboxSelectMultiple
    )


class InterviewForm(forms.ModelForm):
    assignments = forms.ModelMultipleChoiceField(
        label=Interview.assignments.field.verbose_name,
        queryset=(InterviewAssignment.objects
                  .select_related("campaign", "campaign__city")
                  .order_by("-campaign__year", "campaign__city_id", "name")),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
    )

    class Meta:
        model = Interview
        fields = "__all__"
        widgets = {
            'applicant': forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super(InterviewForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper['assignments'].wrap(
            Field, template='admission/forms/assignments_field.html')
        self.helper.layout.append(
            FormActions(Submit('create', _('Create interview')),
                        css_class="pull-right"))

    @staticmethod
    def build_data(applicant, slot):
        date = datetime.combine(slot.stream.date, slot.start_at)
        date = timezone.make_aware(date, applicant.get_city_timezone())
        return {
            'applicant': applicant.pk,
            'status': Interview.APPROVED,
            'interviewers': slot.stream.interviewers.all(),
            'date': date
        }


class InterviewFromStreamForm(forms.Form):
    prefix = "interview_from_stream"

    streams = forms.ModelMultipleChoiceField(
        label=_("Interview streams"),
        queryset=InterviewStream.objects.get_queryset(),
        widget=SelectMultiple(attrs={"size": 1, "class": "bs-select-hidden"}),
        required=True)

    slot = forms.ModelChoiceField(
        label="Время собеседования",
        queryset=InterviewSlot.objects.select_related("stream").none(),
        help_text="",
        required=False)

    def clean(self):
        slot = self.cleaned_data.get("slot")
        streams = self.cleaned_data.get('streams')
        if slot:
            if not streams or slot.stream.pk not in {s.pk for s in streams}:
                raise ValidationError("Выбранный слот должен соответствовать "
                                      "выбранному потоку.")
        # FIXME: applicant.campaign_id должно совпасть с stream.campaign_id
        elif streams:
            empty_slots_qs = (InterviewSlot.objects
                              .filter(interview__isnull=True,
                                      stream_id__in=[s.pk for s in streams]))
            if not empty_slots_qs.exists():
                raise ValidationError("Все слоты заняты.")
        # TODO: Limit active invitations by slots

    def __init__(self, city_code, *args, **kwargs):
        super().__init__(*args, **kwargs)
        stream_field = self.prefix + "-streams"
        if 'data' in kwargs and kwargs['data'].getlist(stream_field):
            stream_ids = kwargs['data'].getlist(stream_field)
            self.fields['slot'].queryset = (InterviewSlot.objects
                                            .select_related("stream")
                                            .filter(stream_id__in=stream_ids))
        today = now_local(city_code).date()
        self.fields['streams'].queryset = (InterviewStream.objects
                                           .filter(venue__city_id=city_code,
                                                   date__gt=today)
                                           .select_related("venue"))
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Div(
                Div(
                    Div('streams', css_class='col-xs-6'),
                    css_class='row'
                ),
                Div(
                    Div('slot', css_class='col-xs-6'),
                    css_class='row'
                ),
                FormActions(Submit('create', _('Send')))
            ))


class InterviewAssignmentsForm(forms.ModelForm):
    prefix = "interview_assignments_form"

    assignments = forms.ModelMultipleChoiceField(
        label=Interview.assignments.field.verbose_name,
        queryset=(InterviewAssignment.objects
                  .select_related("campaign", "campaign__city")
                  .order_by("-campaign__year", "campaign__city_id", "name")),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
    )

    class Meta:
        model = Interview
        fields = ["assignments"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper['assignments'].wrap(
            Field, template='admission/forms/assignments_field.html')
        self.helper.layout.append(
            FormActions(Submit('update', _('Update assignments list'))))
        self.helper.form_class = self.prefix


class InterviewCommentForm(forms.ModelForm):
    use_required_attribute = False

    class Meta:
        model = Comment
        fields = ["text", "score", "interview", "interviewer"]
        widgets = {
            'interview': forms.HiddenInput(),
            'interviewer': forms.HiddenInput(),
            'score': forms.Select(
                choices=(
                    ("", ""),
                    (-2, "не брать ни сейчас, ни потом"),
                    (-1, "не брать сейчас"),
                    (0, "нейтрально"),
                    (1, "можно взять"),
                    (2, "точно нужно взять")),
            ),
            'text': UbereditorWidget(attrs={
                'data-local-persist': 'true',
            })
        }
        error_messages = {
            'score': {
                'required': _("Укажите оценку перед сохранением."),
            },
        }

    def __init__(self, *args, **kwargs):
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Div('score'),
            Div('text'),
            'interview', 'interviewer',
            FormActions(Submit('save', _('Save'))),
        )
        self.interviewer = kwargs.pop("interviewer", None)
        self.interview_id = kwargs.pop("interview_id", None)
        initial = kwargs.get("initial", {})
        initial["interview"] = self.interview_id
        initial["interviewer"] = self.interviewer
        kwargs["initial"] = initial
        self.helper.form_action = reverse("admission:interview_comment",
                                          kwargs={"pk": self.interview_id})
        super().__init__(*args, **kwargs)
        self.fields['score'].label = "Моя оценка"
        self.fields['text'].label = "Комментарий"

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
        exclude = ("campaign", "first_name", "patronymic", "surname",
                   "status", "admin_note", "yandex_id_normalize", "user",
                   "university_other", "contest_id", "participant_id",
                   "is_unsubscribed", "university2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Swap label with help text for next fields
        to_swap = [
            "preferred_study_programs_dm_note",
            "preferred_study_programs_se_note",
        ]
        for field in to_swap:
            self.fields[field].label = self.fields[field].help_text


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
            reverse("admission:applicant_status_update", args=[self.instance.pk]),
            "#update-status-form")


class ResultsModelForm(ModelForm):
    RESULTS_CHOICES = (
        ('', filters_settings.EMPTY_CHOICE_LABEL),
        (Applicant.ACCEPT, "Берём"),
        (Applicant.VOLUNTEER, "Берём в вольные слушатели"),
        (Applicant.ACCEPT_IF, "Берём с условием"),
        (Applicant.REJECTED_BY_INTERVIEW, "Не берём"),
        (Applicant.THEY_REFUSED, "Отказался"),
    )

    class Meta:
        model = Applicant
        fields = ("status",)

    status = forms.ChoiceField(choices=RESULTS_CHOICES,
                               required=False,
                               initial="")

    def clean_status(self):
        """Remains old status if none was provided"""
        new_status = self.cleaned_data["status"]
        if not new_status:
            return self.instance.status
        return new_status


class InterviewStreamChangeForm(ModelForm):
    class Meta:
        model = InterviewSlot
        fields = "__all__"
