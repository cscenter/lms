from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Div, Field, Layout, Row, Submit
from django_filters.conf import settings as filters_settings

from django import forms
from django.core.exceptions import ValidationError
from django.forms import SelectMultiple
from django.forms.models import ModelForm
from django.utils.translation import gettext_lazy as _

from admission.models import (
    Applicant, Comment, Interview, InterviewAssignment, InterviewInvitation,
    InterviewSlot, InterviewStream
)
from core.models import Branch
from core.timezone import now_local
from core.urls import reverse
from core.views import ReadOnlyFieldsMixin
from core.widgets import UbereditorWidget


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
            'interviewers': slot.stream.interviewers.all(),
            'date': slot.datetime_local
        }


class InterviewStreamInvitationForm(forms.Form):
    prefix = "interview_stream_invitation"

    streams = forms.ModelMultipleChoiceField(
        label=_("Interview streams"),
        queryset=InterviewStream.objects.get_queryset(),
        widget=SelectMultiple(attrs={"size": 1, "class": "bs-select-hidden"}),
        required=True)

    def __init__(self, stream, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['streams'].queryset = stream
        self.helper = FormHelper(self)
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
        today = now_local(branch.get_timezone()).date()
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
        self.helper.form_action = reverse("admission:interviews:comment",
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
        if interview.pk != self.interview_id:
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
            reverse("admission:applicants:update_status", args=[self.instance.pk]),
            "#update-status-form")


class ResultsModelForm(ModelForm):
    RESULTS_CHOICES = (
        ('', filters_settings.EMPTY_CHOICE_LABEL),
        (Applicant.ACCEPT, "Берём"),
        (Applicant.VOLUNTEER, "Берём в вольные слушатели"),
        (Applicant.ACCEPT_IF, "Берём с условием"),
        (Applicant.ACCEPT_PAID, "Платное"),
        (Applicant.WAITING_FOR_PAYMENT, "Ожидаем оплаты"),
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
