# -*- coding: utf-8 -*-

from __future__ import absolute_import, unicode_literals

from crispy_forms.bootstrap import FormActions
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Div, Submit
from django import forms
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.forms.models import ModelForm
from django.utils.translation import ugettext_lazy as _

from core.forms import Ubereditor
from core.views import ReadOnlyFieldsMixin
from learning.admission.models import Interview, Comment, Applicant


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


class ApplicantForm(ReadOnlyFieldsMixin, forms.ModelForm):
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
        self.helper.form_action = reverse("admission_applicant_status_update",
                                          args=[self.instance.pk]) + "#update-status-form"


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
