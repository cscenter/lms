from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Layout, Row, Submit
from django_filters.conf import settings as filters_settings

from django import forms
from django.core.exceptions import ValidationError
from django.db import transaction
from django.forms import SelectMultiple
from django.forms.models import ModelForm
from django.utils.translation import gettext_lazy as _

from admission.constants import ApplicantStatuses
from admission.models import (
    Acceptance, Applicant, Comment, Interview, InterviewAssignment, InterviewSlot,
    InterviewStream
)
from admission.services import (
    AccountData, StudentProfileData, create_student, validate_verification_code
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
        queryset=(InterviewAssignment.objects
                  .select_related("campaign", "campaign__branch")
                  .order_by("-campaign__year", "campaign__branch_id", "name")),
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
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper['assignments'].wrap(
            Field, template='admission/forms/assignments_field.html')
        self.helper.layout.append(
            FormActions(Submit('create', _('Create interview')),
                        css_class="pull-right"))

    @staticmethod
    def build_data(applicant, slot):
        return {
            'applicant': applicant.pk,
            'status': Interview.APPROVED,
            'section': slot.stream.section,
            'venue': slot.stream.venue,
            'interviewers': slot.stream.interviewers.all(),
            'date': slot.datetime_local
        }


class InterviewStreamInvitationForm(forms.Form):
    streams = forms.ModelMultipleChoiceField(
        label=_("Interview streams"),
        queryset=InterviewStream.objects.none(),
        widget=SelectMultiple(attrs={"size": 1, "class": "bs-select-hidden multiple-select"}),
        required=True)

    def __init__(self, streams, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['streams'].queryset = streams
        self.helper = FormHelper(self)
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Div('streams', css_class='col-xs-8'),
                Div(Submit('create-invitation', _('Пригласить на собеседование'),
                           css_class="btn btn-primary btn-outline "
                                     "btn-block -inline-submit"),
                    css_class="col-xs-4"),
            ))


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

    def __init__(self, branch: Branch, *args, **kwargs):
        super().__init__(*args, **kwargs)
        stream_field = self.prefix + "-streams"
        if 'data' in kwargs and kwargs['data'].getlist(stream_field):
            stream_ids = kwargs['data'].getlist(stream_field)
            self.fields['slot'].queryset = (InterviewSlot.objects
                                            .select_related("stream")
                                            .filter(stream_id__in=stream_ids))
        tz = branch.get_timezone()
        assert tz is not None
        today = now_local(tz).date()
        self.fields['streams'].queryset = (InterviewStream.objects
                                           .filter(campaign__branch=branch,
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
                  .select_related("campaign", "campaign__branch")
                  .order_by("-campaign__year", "campaign__branch_id", "name")),
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
            'score': forms.Select(),
            'text': UbereditorWidget(attrs={
                'data-local-persist': 'true',
            })
        }
        error_messages = {
            'score': {
                'required': _("Укажите оценку перед сохранением."),
            },
        }

    def __init__(self, interview: Interview, interviewer, **kwargs):
        self.interview = interview
        self.interviewer = interviewer
        kwargs["initial"] = {
            **kwargs.get("initial", {}),
            "interview": self.interview,
            "interviewer": self.interviewer
        }
        super().__init__(**kwargs)
        self.fields['score'].label = "Моя оценка"
        score_choices = (('', filters_settings.EMPTY_CHOICE_LABEL),
                         *interview.rating_system.choices)
        self.fields['score'].widget.choices = score_choices
        self.fields['score'].choices = interview.rating_system.choices
        self.fields['text'].label = "Комментарий"
        self.helper = FormHelper(self)
        self.helper.layout = Layout(
            Div('score'),
            Div('text'),
            'interview', 'interviewer',
            FormActions(Submit('save', _('Save'))),
        )
        self.helper.form_action = reverse("admission:interviews:comment",
                                          kwargs={"pk": self.interview.pk})

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
        if interview != self.interview:
            raise ValidationError("Submitted interview id not match GET-value")
        return interview


class ApplicantReadOnlyForm(ReadOnlyFieldsMixin, forms.ModelForm):
    readonly_fields = "__all__"

    class Meta:
        model = Applicant
        exclude = ("campaign", "first_name", "patronymic", "last_name",
                   "status", "yandex_login_q", "user",
                   "university_other", "contest_id", "participant_id",
                   "is_unsubscribed",)

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Swap label with help text for next fields
        to_swap = [
            "preferred_study_programs_dm_note",
            "preferred_study_programs_se_note",
        ]
        for field in to_swap:
            self.fields[field].label = self.fields[field].help_text
        if not request.user.is_curator:
            del self.fields['admin_note']


class ApplicantForm(forms.ModelForm):
    class Meta:
        model = Applicant
        fields = ("admin_note", "status")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper(self)
        self.helper.layout.append(
            FormActions(Submit('update', _('Update')), css_class="pull-right"))
        self.helper.form_action = "{}{}".format(
            reverse("admission:applicants:update_status", args=[self.instance.pk]),
            "#update-status-form")


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
        ('', filters_settings.EMPTY_CHOICE_LABEL),
        (ApplicantStatuses.ACCEPT, "Берём"),
        (ApplicantStatuses.VOLUNTEER, "Берём в вольные слушатели"),
        (ApplicantStatuses.ACCEPT_IF, "Берём с условием"),
        (ApplicantStatuses.ACCEPT_PAID, "Платное"),
        (ApplicantStatuses.WAITING_FOR_PAYMENT, "Ожидаем оплаты"),
        (ApplicantStatuses.REJECTED_BY_INTERVIEW, "Не берём"),
        (ApplicantStatuses.REJECTED_BY_INTERVIEW_WITH_BONUS, "Не берём, предложили билет"),
        (ApplicantStatuses.THEY_REFUSED, "Отказался"),
    )

    class Meta:
        model = Applicant
        fields = ("status",)

    status = ApplicantFinalStatusField(choices=FINAL_CHOICES,
                                       required=False,
                                       initial="")

    def clean_status(self) -> str:
        """Remains old status if none was provided"""
        new_status = self.cleaned_data["status"]
        if not new_status:
            return self.instance.status
        return new_status

    def save(self, commit=True) -> Applicant:
        instance = super().save(commit=False)
        instance.save(update_fields=['status'])
        self.save_m2m()
        return instance


class InterviewStreamChangeForm(ModelForm):
    class Meta:
        model = InterviewSlot
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
                Div(
                    Div('authorization_code', css_class='col-xs-6'),
                    css_class='row'
                ),
                FormActions(Submit('create', _('Send')))
            ))

    def clean_authorization_code(self) -> str:
        code = self.cleaned_data['authorization_code']
        if code and code != self.instance.confirmation_code:
            raise ValidationError(_("Authorization code is invalid."))
        return code


class ConfirmationForm(forms.ModelForm):
    prefix = "confirmation"

    authorization_code = forms.CharField(
        required=True,
        widget=forms.HiddenInput())
    email_code = forms.CharField(
        label="Email Confirmation Code",
        help_text="Нажмите «Прислать код», затем введите код из сообщения, отправленного на email.",
        required=True,
        widget=forms.TextInput(attrs={"placeholder": "Код подтверждения"}))
    birth_date = forms.DateField(label=_("Birthday"), required=True)
    telegram_username = forms.CharField(
        label="Имя пользователя в Telegram",
        help_text="@&lt;<b>username</b>&gt; в настройках профиля Telegram."
                  "<br>Поставьте прочерк «-», если аккаунт отсутствует.",
        required=True
    )
    # Student Profile data

    class Meta:
        model = User
        fields = [
            "email",
            "email_code",
            "time_zone",
            "gender",
            "birth_date",
            "photo",
            "phone",
            "telegram_username",
            "workplace",
            "private_contacts",
            # Read-only fields (some of them are not a part of User model)
            "yandex_login",
            "codeforces_login",
            "stepic_id",
            "github_login",
        ]

    def __init__(self, acceptance: Acceptance, **kwargs):
        self.acceptance = acceptance
        applicant = acceptance.applicant
        initial = {
            "authorization_code": acceptance.confirmation_code,
            "email": applicant.email,
            "time_zone": applicant.campaign.get_timezone(),
            "phone": applicant.phone,
            "yandex_login": applicant.yandex_login,
            "stepic_id": applicant.stepic_id,
            "github_login": applicant.github_login,
            "workplace": applicant.workplace,
            "birth_date": applicant.birth_date,
        }
        kwargs["initial"] = initial
        super().__init__(**kwargs)
        self.fields['photo'].required = True
        self.fields['photo'].help_text = "Изображение в формате JPG или PNG (мин. 250х350px). Размер файла не более 3Mb"
        self.fields['yandex_login'].disabled = True
        self.fields['phone'].required = True
        self.fields['private_contacts'].help_text = ""
        self.helper = FormHelper(self)
        self.helper.form_tag = False

    def clean_authorization_code(self):
        code = self.cleaned_data.get('authorization_code')
        if code != self.acceptance.confirmation_code:
            raise ValidationError(_("Authorization code is not valid"))

    def clean_telegram_username(self):
        telegram_username = self.cleaned_data.get('telegram_username')
        telegram_username = telegram_username.replace('@', '')
        return "" if len(telegram_username) == 1 else telegram_username

    def clean(self):
        email = self.cleaned_data.get('email')
        email_code = self.cleaned_data.get('email_code')
        if email and email_code:
            is_valid_email_code = validate_verification_code(self.acceptance.applicant,
                                                             email,
                                                             email_code)
            if not is_valid_email_code:
                self.add_error("email_code", _("Email verification code is not valid"))

    def save(self, commit=True) -> User:
        account_data = AccountData.from_dict(self.cleaned_data)
        student_profile_data = StudentProfileData(
            university=self.acceptance.applicant.get_university_display()
        )
        with transaction.atomic():
            user = create_student(self.acceptance, account_data, student_profile_data)
        return user
