from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Layout, Row, Submit
from django_filters.conf import settings as filters_settings

from django import forms
from django.core.exceptions import ValidationError
from django.forms import SelectMultiple
from django.forms.models import ModelForm
from django.utils.translation import gettext_lazy as _

from admission.constants import ApplicantStatuses
from admission.models import (
    Acceptance,
    Applicant,
    Comment,
    Interview,
    InterviewAssignment,
    InterviewSlot,
    InterviewStream,
)
from admission.services import (
    AccountData,
    StudentProfileData,
    create_student,
    validate_verification_code,
)
from core.models import Branch
from core.timezone import now_local
from core.urls import reverse
from core.views import ReadOnlyFieldsMixin
from core.widgets import UbereditorWidget
from users.models import User


class InterviewForm(forms.ModelForm):
    assignments = forms.ModelMultipleChoiceField(
        label=Interview.assignments.field.verbose_name,
        queryset=(
            InterviewAssignment.objects.select_related(
                "campaign", "campaign__branch"
            ).order_by("-campaign__year", "campaign__branch_id", "name")
        ),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
    )

    class Meta:
        model = Interview
        fields = "__all__"
        widgets = {
            "applicant": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper["assignments"].wrap(
            Field, template="admission/forms/assignments_field.html"
        )
        self.helper.layout.append(
            FormActions(Submit("create", _("Create interview")), css_class="pull-right")
        )

    @staticmethod
    def build_data(applicant, slot):
        return {
            "applicant": applicant.pk,
            "status": Interview.APPROVED,
            "section": slot.stream.section,
            "format": slot.stream.format,
            "venue": slot.stream.venue,
            "interviewers": slot.stream.interviewers.all(),
            "date": slot.datetime_local,
            "duration": slot.stream.duration
        }


class InterviewStreamInvitationForm(forms.Form):
    streams = forms.ModelMultipleChoiceField(
        label=_("Interview streams"),
        queryset=InterviewStream.objects.none(),
        widget=SelectMultiple(
            attrs={"size": 1, "class": "bs-select-hidden multiple-select"}
        ),
        required=True,
    )

    def __init__(self, streams, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["streams"].queryset = streams.prefetch_related('interviewers')
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Div("streams", css_class="col-xs-8"),
                Div(
                    Submit(
                        "create-invitation",
                        _("Пригласить на собеседование"),
                        css_class="btn btn-primary btn-outline "
                                  "btn-block -inline-submit",
                    ),
                    css_class="col-xs-4",
                ),
            )
        )


class InterviewFromStreamForm(forms.Form):
    prefix = "interview_from_stream"

    streams = forms.ModelMultipleChoiceField(
        label=_("Interview streams"),
        queryset=InterviewStream.objects.get_queryset(),
        widget=SelectMultiple(attrs={"size": 1, "class": "bs-select-hidden"}),
        required=True,
    )

    slot = forms.ModelChoiceField(
        label="Время собеседования",
        queryset=InterviewSlot.objects.select_related("stream").none(),
        help_text="",
        required=False,
    )

    def clean(self):
        slot = self.cleaned_data.get("slot")
        streams = self.cleaned_data.get("streams")
        if slot:
            if not streams or slot.stream.pk not in {s.pk for s in streams}:
                raise ValidationError(
                    "Выбранный слот должен соответствовать " "выбранному потоку."
                )
        # FIXME: applicant.campaign_id должно совпасть с stream.campaign_id
        elif streams:
            empty_slots_qs = InterviewSlot.objects.filter(
                interview__isnull=True, stream_id__in=[s.pk for s in streams]
            )
            if not empty_slots_qs.exists():
                raise ValidationError("Все слоты заняты.")
        # TODO: Limit active invitations by slots

    def __init__(self, branch: Branch, *args, **kwargs):
        super().__init__(*args, **kwargs)
        stream_field = self.prefix + "-streams"
        if "data" in kwargs and kwargs["data"].getlist(stream_field):
            stream_ids = kwargs["data"].getlist(stream_field)
            self.fields["slot"].queryset = InterviewSlot.objects.select_related(
                "stream"
            ).filter(stream_id__in=stream_ids)
        tz = branch.get_timezone()
        assert tz is not None
        today = now_local(tz).date()
        self.fields["streams"].queryset = InterviewStream.objects.filter(
            campaign__branch=branch, date__gt=today
        ).select_related("venue")
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Div(
                Div(Div("streams", css_class="col-xs-6"), css_class="row"),
                Div(Div("slot", css_class="col-xs-6"), css_class="row"),
                FormActions(Submit("create", _("Send"))),
            )
        )


class InterviewAssignmentsForm(forms.ModelForm):
    prefix = "interview_assignments_form"

    assignments = forms.ModelMultipleChoiceField(
        label=Interview.assignments.field.verbose_name,
        queryset=(
            InterviewAssignment.objects.select_related(
                "campaign", "campaign__branch"
            ).order_by("-campaign__year", "campaign__branch_id", "name")
        ),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
    )

    class Meta:
        model = Interview
        fields = ["assignments"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper["assignments"].wrap(
            Field, template="admission/forms/assignments_field.html"
        )
        self.helper.layout.append(
            FormActions(Submit("update", _("Update assignments list")))
        )
        self.helper.form_class = self.prefix


class InterviewCommentForm(forms.ModelForm):
    use_required_attribute = False

    class Meta:
        model = Comment
        fields = ["text", "score", "interview", "interviewer"]
        widgets = {
            "interview": forms.HiddenInput(),
            "interviewer": forms.HiddenInput(),
            "score": forms.Select(),
            "is_cancelled": forms.CheckboxInput(),
            "text": UbereditorWidget(
                attrs={
                    "data-local-persist": "true",
                }
            ),
        }
        error_messages = {
            "score": {
                "required": _("Укажите оценку перед сохранением."),
            },
        }

    def __init__(self, interview: Interview, interviewer, **kwargs):
        self.interview = interview
        self.interviewer = interviewer
        kwargs["initial"] = {
            **kwargs.get("initial", {}),
            "interview": self.interview,
            "interviewer": self.interviewer,
        }
        super().__init__(**kwargs)
        self.fields["is_cancelled"] = forms.BooleanField(
            required=False,
            label=_("Is Cancelled"),
            initial=self.interview.status == interview.CANCELED,
        )
        self.fields["score"].required = False
        self.fields["score"].label = "Моя оценка"
        score_choices = (
            ("", filters_settings.EMPTY_CHOICE_LABEL),
            *interview.rating_system.choices,
        )
        self.fields["score"].widget.choices = score_choices
        self.fields["score"].choices = interview.rating_system.choices
        self.fields["text"].label = "Комментарий"
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Div(Div("score", css_class="col-xs-8"), Div("is_cancelled", css_class="col-xs-4", style="top: 12px;"),
                css_class="row"),
            Div("text"),
            "interview",
            "interviewer",
            FormActions(Submit("save", _("Save"))),
        )
        self.helper.form_action = reverse(
            "admission:interviews:comment", kwargs={"pk": self.interview.pk}
        )

    def clean_interviewer(self):
        interviewer = self.cleaned_data["interviewer"]
        if not self.interviewer or (
            interviewer != self.interviewer and not self.interviewer.is_curator
        ):
            raise ValidationError(
                _(
                    "Sorry, but you should be in interviewers list to "
                    "create or update comment."
                )
            )
        return interviewer

    def clean_interview(self):
        interview = self.cleaned_data["interview"]
        if interview != self.interview:
            raise ValidationError("Submitted interview id not match GET-value")
        return interview

    def clean(self):
        cleaned_data = super().clean()
        is_cancelled = cleaned_data.get('is_cancelled')
        score = cleaned_data.get('score')

        if is_cancelled and self.interview.status not in (self.interview.CANCELED, self.interview.APPROVED):
            self.add_error('is_cancelled', _('Интервью не может быть помечено как отмененное, если оно не имеет '
                                             'статус "Согласовано"'))

        if (is_cancelled and self.interview.status == self.interview.CANCELED) or \
            (not is_cancelled and self.interview.status != self.interview.CANCELED) \
            and not score:
            self.add_error('score', self.fields['score'].error_messages['required'])

        return cleaned_data

    def save(self, commit=True):
        comment = super().save(commit=False)
        is_cancelled = self.cleaned_data['is_cancelled']
        if commit:
            if is_cancelled and self.interview.status == self.interview.APPROVED:
                self.interview.status = self.interview.CANCELED
                self.interview.save()
            elif not is_cancelled and self.interview.status == self.interview.CANCELED:
                self.interview.status = self.interview.APPROVED
                self.interview.save()
            else:
                comment.save()
        return comment


class ApplicantReadOnlyForm(ReadOnlyFieldsMixin, forms.ModelForm):
    readonly_fields = "__all__"

    class Meta:
        model = Applicant
        exclude = (
            "campaign",
            "first_name",
            "patronymic",
            "last_name",
            "status",
            "yandex_login_q",
            "user",
            "university_other",
            "contest_id",
            "participant_id",
            "is_unsubscribed",
            'stepic_id',
            'github_login',
            'graduate_work',
            'online_education_experience',
            'probability',
            'preferred_study_programs',
            'preferred_study_program_notes',
            'preferred_study_programs_dm_note',
            'preferred_study_programs_se_note',
            'preferred_study_programs_cs_note',
            'your_future_plans'
        )

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not request.user.is_curator:
            del self.fields["admin_note"]


class ApplicantForm(forms.ModelForm):
    class Meta:
        model = Applicant
        fields = ("admin_note", "status")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(
            FormActions(Submit("update", _("Update")), css_class="pull-right")
        )
        self.helper.form_action = "{}{}".format(
            reverse("admission:applicants:update_status", args=[self.instance.pk]),
            "#update-status-form",
        )


class ApplicantFinalStatusField(forms.ChoiceField):
    def has_changed(self, initial, data) -> bool:
        has_changed = super().has_changed(initial, data)
        # Empty `status` value means we didn't set any final status and
        # the previous status should be preserved - make it inside
        # ModelForm where instance is accessible, e.g. inside
        # `clean_status` hook
        if has_changed and not data:
            return False
        return has_changed


class ApplicantFinalStatusForm(ModelForm):
    FINAL_CHOICES = (
        ("", filters_settings.EMPTY_CHOICE_LABEL),
        (ApplicantStatuses.ACCEPT, "Берём"),
        (ApplicantStatuses.ACCEPT_IF, "Берём с условием"),
        (ApplicantStatuses.ACCEPT_PAID, "Платное"),
        (ApplicantStatuses.REJECTED_BY_INTERVIEW, "Не берём"),
        (
            ApplicantStatuses.REJECTED_BY_INTERVIEW_WITH_BONUS,
            "Не берём, предложили билет",
        ),
        (ApplicantStatuses.THEY_REFUSED, "Отказался"),
    )

    class Meta:
        model = Applicant
        fields = ("status",)

    status = ApplicantFinalStatusField(
        choices=FINAL_CHOICES, required=False, initial=""
    )

    def clean_status(self) -> str:
        """Remains old status if none was provided"""
        new_status = self.cleaned_data["status"]
        if not new_status:
            return self.instance.status
        return new_status

    def save(self, commit=True) -> Applicant:
        instance = super().save(commit=False)
        instance.save(update_fields=["status"])
        self.save_m2m()
        return instance


class InterviewStreamChangeForm(ModelForm):
    class Meta:
        model = InterviewStream
        fields = "__all__"


class ConfirmationAuthorizationForm(forms.Form):
    prefix = "auth"

    authorization_code = forms.CharField(label=_("Code"), required=True)

    def __init__(self, instance: Acceptance, *args, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Div(
                Div(Div("authorization_code", css_class="col-xs-6"), css_class="row"),
                FormActions(Submit("create", _("Send"))),
            )
        )

    def clean_authorization_code(self) -> str:
        code = self.cleaned_data["authorization_code"]
        if code and code != self.instance.confirmation_code:
            raise ValidationError(_("Authorization code is invalid."))
        return code


class ConfirmationForm(forms.ModelForm):
    prefix = "confirmation"

    disabled = ["first_name",
                "last_name",
                "patronymic",
                "branch",
                "track",
                "yandex_login"]

    force_required = ["phone",
                      "living_place"]

    authorization_code = forms.CharField(required=True, widget=forms.HiddenInput())
    email_code = forms.CharField(
        label="Email Confirmation Code",
        help_text="Нажмите «Прислать код», затем введите код из сообщения, отправленного на email.",
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Код подтверждения"}),
    )
    birth_date = forms.DateField(label=_("Birthday"), required=True)
    telegram_username = forms.CharField(
        label="Имя пользователя в Telegram",
        help_text="@<<b>username</b>> в настройках профиля Telegram."
                  "<br>Поставьте прочерк «-», если аккаунт отсутствует.",
        required=True,
    )
    yandex_login = forms.CharField(
        label=_("Yandex Login"),
        required=False,
        help_text="Яндекс логин можно будет поменять в личном кабинете во время обучения"
    )
    has_no_patronymic = forms.BooleanField(
            label=_("Has no patronymic"),
            required=False
        )
    branch = forms.CharField(
        label=_("Branch"),
        required=False
    )
    track = forms.CharField(
        label=_("Admission track"),
        required=False
    )
    comment = forms.CharField(
        required=False,
        widget=forms.Textarea
    )
    offer_confirmation = forms.BooleanField(
            label='Я подтверждаю свое ознакомление и согласие с <a '
                  'href="https://yandex.ru/legal/dataschool_offer/">Офертой на оказание услуг дополнительного '
                  'профессионального образования для физических лиц </a>'
                  'и с <a href="https://yandex.ru/legal/dataschool_termsofuse/">'
                  'Условиями использования сервиса «LMS Школы анализа данных»</a>',
            required=True
        )
    personal_data_confirmation = forms.BooleanField(
            label='Даю согласие АНО ДПО "ОБРАЗОВАТЕЛЬНЫЕ ТЕХНОЛОГИИ ЯНДЕКСА" (ОГРН: 1147799006123), '
                  'ООО "ЯНДЕКС" (ОГРН: 1027700229193), АО "АЭРОКЛУБ" (ОГРН: 1027739037622), '
                  'ООО "АГЕНТСТВО АВИА ЦЕНТР" (ОГРН: 1077758118063), '
                  'а также транспортным компаниям, гостиницам и компаниям, осуществляющим визовое сопровождение, '
                  'на обработку указанных мной персональных данных в целях организации поездок, '
                  'а именно для покупки билетов, оформления бронирований, '
                  'организации получения разрешительной документации на посещение стран прибытия. '
                  'Мне известно о моем праве в любое время отозвать настоящее согласия путем направления письма '
                  'на электронный адрес: agreements@yandex-team.ru.',
            required=True
        )

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "patronymic",
            "email",
            "email_code",
            "living_place",
            "gender",
            "birth_date",
            "phone",
            "telegram_username",
            "yandex_login",
        ]

    def __init__(self, acceptance: Acceptance, **kwargs):
        self.acceptance = acceptance
        applicant: Applicant = acceptance.applicant
        initial = {
            "first_name": applicant.first_name,
            "last_name": applicant.last_name,
            "patronymic": applicant.patronymic,
            "branch": applicant.campaign.branch.name,
            "track": _("Alternative") if applicant.new_track else _("Regular"),
            "gender": applicant.gender,
            "living_place": applicant.residence_city if applicant.residence_city else applicant.living_place,
            "authorization_code": acceptance.confirmation_code,
            "email": applicant.email,
            "phone": applicant.phone,
            "yandex_login": applicant.yandex_login,
            "telegram_username": f"@{applicant.telegram_username}",
            "birth_date": applicant.birth_date
        }
        kwargs["initial"] = initial
        super().__init__(**kwargs)
        for field_name in self.disabled:
            self.fields[field_name].disabled = True
        for field_name in self.force_required:
            self.fields[field_name].required = True
        self.fields["email"].help_text = "Если у вас уже была учётная запись на сайте ШАДа, то введите ту электронную почту, которую использовали ранее"
        self.helper = FormHelper(self)
        self.helper.form_tag = False

    def clean_authorization_code(self):
        code = self.cleaned_data.get("authorization_code")
        if code != self.acceptance.confirmation_code:
            raise ValidationError(_("Authorization code is not valid"))

    def clean_telegram_username(self):
        telegram_username = self.cleaned_data.get("telegram_username")
        telegram_username = telegram_username.replace("@", "")
        return "" if len(telegram_username) == 1 else telegram_username

    def clean(self):
        email = self.cleaned_data.get("email")
        email_code = self.cleaned_data.get("email_code")
        if email and email_code:
            is_valid_email_code = validate_verification_code(
                self.acceptance.applicant, email, email_code
            )
            if not is_valid_email_code:
                self.add_error("email_code", _("Email verification code is not valid"))

    def save(self, commit=True) -> User:
        account_data_data = self.cleaned_data.copy()
        account_data = AccountData.from_dict(account_data_data)
        profile_data = StudentProfileData.from_dict(self.cleaned_data)
        return create_student(self.acceptance, account_data, profile_data)
